#!/usr/bin/env python3
"""Tests for benchmarking functionality."""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from nix_hyperfine.benchmark import BenchmarkMode, benchmark_build, benchmark_eval
from nix_hyperfine.exceptions import NixError
from nix_hyperfine.parser import parse_args, parse_derivation_spec
from nix_hyperfine.specs import DerivationSpec


@pytest.mark.parametrize(
    ("mode", "benchmark_func"),
    [
        (BenchmarkMode.BUILD, benchmark_build),
        (BenchmarkMode.EVAL, benchmark_eval),
    ],
)
def test_benchmark_success(
    tmp_path: Path,
    mode: BenchmarkMode,  # noqa: ARG001
    benchmark_func: Callable[[list[DerivationSpec], list[str]], None],
) -> None:
    """Test successful benchmarking in both build and eval modes."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    derivation {
      name = "test-success";
      system = builtins.currentSystem;
      builder = "/bin/sh";
      args = [ "-c" "echo 'test' > $out" ];
    }
    """)

    spec = parse_derivation_spec(f"-f {nix_file}")

    # Run benchmark - should complete without error
    benchmark_func([spec], ["--runs", "1"])


def test_benchmark_multiple_specs(tmp_path: Path) -> None:
    """Test benchmarking multiple derivations."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    {
      fast = derivation {
        name = "fast";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo fast > $out" ];
      };
      slow = derivation {
        name = "slow";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "sleep 0.05; echo slow > $out" ];
      };
    }
    """)

    # Parse multiple specs
    spec1 = parse_derivation_spec(f"-f {nix_file} -A fast")
    spec2 = parse_derivation_spec(f"-f {nix_file} -A slow")

    # Verify the raw field contains the original spec (for naming)
    assert spec1.raw == f"-f {nix_file} -A fast"
    assert spec2.raw == f"-f {nix_file} -A slow"

    # Run benchmark with multiple specs
    benchmark_build([spec1, spec2], ["--runs", "1"])


@pytest.mark.parametrize(
    ("test_name", "nix_configs"),
    [
        # Single failing build
        (
            "single_failure",
            [
                {
                    "content": """
                    derivation {
                      name = "failing-build";
                      system = builtins.currentSystem;
                      builder = "/bin/sh";
                      args = [ "-c" "exit 1" ];
                    }
                    """,
                    "should_fail": True,
                },
            ],
        ),
        # Success then failure
        (
            "success_then_failure",
            [
                {
                    "content": """
                    derivation {
                      name = "working-build";
                      system = builtins.currentSystem;
                      builder = "/bin/sh";
                      args = [ "-c" "echo 'success' > $out" ];
                    }
                    """,
                    "should_fail": False,
                },
                {
                    "content": """
                    derivation {
                      name = "failing-build";
                      system = builtins.currentSystem;
                      builder = "/bin/sh";
                      args = [ "-c" "exit 1" ];
                    }
                    """,
                    "should_fail": True,
                },
            ],
        ),
    ],
)
def test_benchmark_build_failures(
    tmp_path: Path,
    test_name: str,  # noqa: ARG001
    nix_configs: list[dict],
) -> None:
    """Test benchmarking with build failures in various configurations."""
    specs = []
    for i, config in enumerate(nix_configs):
        nix_file = tmp_path / f"test_{i}.nix"
        nix_file.write_text(config["content"])
        specs.append(parse_derivation_spec(f"-f {nix_file}"))

    # Should raise NixError during pre-build phase
    with pytest.raises(NixError) as exc_info:
        benchmark_build(specs, ["--runs", "1"])

    # Build failures during pre-build phase
    assert exc_info.value.returncode is not None
    assert "Command failed" in str(exc_info.value)


def test_benchmark_eval_failure(tmp_path: Path) -> None:
    """Test benchmarking when evaluation fails."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    # This will fail during evaluation
    throw "Evaluation error for testing"
    """)

    spec = parse_derivation_spec(f"-f {nix_file}")

    # Run benchmark - should raise NixError during pre-build phase
    with pytest.raises(NixError) as exc_info:
        benchmark_eval([spec], ["--runs", "1"])

    # Evaluation failures will happen during pre-build
    assert exc_info.value.returncode is not None
    assert "Command failed" in str(exc_info.value)


def test_git_revision_with_build_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_env: None,  # noqa: ARG001
) -> None:
    """Test git revision comparison where builds fail in different revisions."""
    # Create a simple git repo
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    # Initialize git repo
    monkeypatch.chdir(repo_dir)
    subprocess.run(["git", "init"], check=True)

    # Create initial version that builds successfully
    nix_content_success = """
    {
      test = derivation {
        name = "test-success";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo 'success' > $out" ];
      };
    }
    """
    nix_path = repo_dir / "default.nix"
    nix_path.write_text(nix_content_success)

    subprocess.run(["git", "add", "default.nix"], check=True)
    subprocess.run(["git", "commit", "-m", "Working version"], check=True)

    # Create second version that fails to build
    nix_content_fail = """
    {
      test = derivation {
        name = "test-fail";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo 'This will fail' >&2; exit 1" ];
      };
    }
    """
    nix_path.write_text(nix_content_fail)
    subprocess.run(["git", "add", "default.nix"], check=True)
    subprocess.run(["git", "commit", "-m", "Failing version"], check=True)

    # Create third version that succeeds again
    nix_content_success2 = """
    {
      test = derivation {
        name = "test-success2";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo 'success again' > $out" ];
      };
    }
    """
    nix_path.write_text(nix_content_success2)
    subprocess.run(["git", "add", "default.nix"], check=True)
    subprocess.run(["git", "commit", "-m", "Fixed version"], check=True)

    # Test parsing with git revisions - success, fail, success
    argv = ["nix-hyperfine", "test@HEAD~2,HEAD~1,HEAD", "--", "--runs", "1"]
    args = parse_args(argv)

    assert len(args.specs) == 3
    assert args.mode == BenchmarkMode.BUILD
    assert args.hyperfine_args == ["--runs", "1"]

    # The raw field should preserve the original spec with revision
    assert args.specs[0].raw == "test@HEAD~2"
    assert args.specs[1].raw == "test@HEAD~1"
    assert args.specs[2].raw == "test@HEAD"

    # Now test that benchmarking fails on the middle revision
    with pytest.raises(NixError) as exc_info:
        benchmark_build(args.specs, args.hyperfine_args)

    assert exc_info.value.returncode is not None
    assert "Command failed" in str(exc_info.value)


def test_git_revision_with_eval_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_env: None,  # noqa: ARG001
) -> None:
    """Test git revision comparison where evaluation fails in some revisions."""
    # Create a simple git repo
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    # Initialize git repo
    monkeypatch.chdir(repo_dir)
    subprocess.run(["git", "init"], check=True)

    # Create initial version that evaluates successfully
    nix_content_success = """
    {
      test = derivation {
        name = "test-eval-success";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo 'success' > $out" ];
      };
    }
    """
    nix_path = repo_dir / "default.nix"
    nix_path.write_text(nix_content_success)

    subprocess.run(["git", "add", "default.nix"], check=True)
    subprocess.run(["git", "commit", "-m", "Working evaluation"], check=True)

    # Create second version that fails during evaluation
    nix_content_eval_fail = """
    {
      test = throw "Evaluation failure in revision";
    }
    """
    nix_path.write_text(nix_content_eval_fail)
    subprocess.run(["git", "add", "default.nix"], check=True)
    subprocess.run(["git", "commit", "-m", "Evaluation failure"], check=True)

    # Test parsing with git revisions - one success, one eval failure
    argv = ["nix-hyperfine", "--eval", "test@HEAD~1,HEAD", "--", "--runs", "1"]
    args = parse_args(argv)

    assert len(args.specs) == 2
    assert args.mode == BenchmarkMode.EVAL

    # The raw field should preserve the original spec with revision
    assert args.specs[0].raw == "test@HEAD~1"
    assert args.specs[1].raw == "test@HEAD"

    # Now test that benchmarking fails on the evaluation
    with pytest.raises(NixError) as exc_info:
        benchmark_eval(args.specs, args.hyperfine_args)

    assert exc_info.value.returncode is not None
    assert "Command failed" in str(exc_info.value)
