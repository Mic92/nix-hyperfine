#!/usr/bin/env python3
"""Tests for git revision functionality."""

import subprocess
from pathlib import Path

import pytest

from nix_hyperfine.benchmark import BenchmarkMode
from nix_hyperfine.parser import expand_git_revisions, parse_args


def test_expand_git_revisions_no_revision() -> None:
    """Test expand_git_revisions with no revision."""
    result = expand_git_revisions("hello")
    assert len(result) == 1
    assert result[0].base_spec == "hello"
    assert result[0].revision is None


def test_expand_git_revisions_single_revision() -> None:
    """Test expand_git_revisions with single revision."""
    result = expand_git_revisions("hello@HEAD~1")
    assert len(result) == 1
    assert result[0].base_spec == "hello"
    assert result[0].revision == "HEAD~1"


def test_expand_git_revisions_multiple_revisions() -> None:
    """Test expand_git_revisions with multiple revisions."""
    result = expand_git_revisions("hello@HEAD~1,HEAD,main")
    assert len(result) == 3
    assert result[0].base_spec == "hello"
    assert result[0].revision == "HEAD~1"
    assert result[1].base_spec == "hello"
    assert result[1].revision == "HEAD"
    assert result[2].base_spec == "hello"
    assert result[2].revision == "main"


def test_expand_git_revisions_with_flake() -> None:
    """Test expand_git_revisions with flake reference."""
    result = expand_git_revisions("nixpkgs#hello@v23.11")
    assert len(result) == 1
    assert result[0].base_spec == "nixpkgs#hello"
    assert result[0].revision == "v23.11"


def test_expand_git_revisions_with_file_spec() -> None:
    """Test expand_git_revisions with file specification."""
    result = expand_git_revisions("-f default.nix -A hello@HEAD~1,HEAD")
    assert len(result) == 2
    assert result[0].base_spec == "-f default.nix -A hello"
    assert result[0].revision == "HEAD~1"
    assert result[1].base_spec == "-f default.nix -A hello"
    assert result[1].revision == "HEAD"


def test_git_revision_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_env: None,  # noqa: ARG001
) -> None:
    """Test git revision expansion with real git repo."""
    # Create a simple git repo
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    monkeypatch.chdir(repo_dir)

    # Get the current system - use builtins.currentSystem evaluation as fallback
    try:
        result = subprocess.run(
            [
                "nix",
                "--extra-experimental-features",
                "nix-command flakes",
                "config",
                "show",
                "system",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        current_system = result.stdout.strip()
    except subprocess.CalledProcessError:
        # Fallback: evaluate builtins.currentSystem
        result = subprocess.run(
            ["nix", "eval", "--expr", "builtins.currentSystem"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_system = result.stdout.strip().strip('"')

    # Create initial flake with raw derivation
    flake_content = f"""
    {{
      outputs = {{ self }}:
      let
        system = "{current_system}";
      in {{
        packages.${{system}}.test = derivation {{
          name = "test-v1";
          inherit system;
          builder = "/bin/sh";
          args = [ "-c" "echo 'version 1' > $out" ];
        }};
      }};
    }}
    """
    flake_path = repo_dir / "flake.nix"
    flake_path.write_text(flake_content)

    subprocess.run(["git", "add", "flake.nix"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)

    # Create second version
    flake_content_v2 = flake_content.replace("version 1", "version 2").replace("test-v1", "test-v2")
    flake_path.write_text(flake_content_v2)
    subprocess.run(["git", "add", "flake.nix"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Version 2"], cwd=repo_dir, check=True)

    # Test parsing with git revisions
    argv = ["nix-hyperfine", "--eval", ".#test@HEAD~1,HEAD", "--", "--runs", "1"]
    args = parse_args(argv)

    assert len(args.specs) == 2
    assert args.mode == BenchmarkMode.EVAL
    assert args.hyperfine_args == ["--runs", "1"]

    # The raw field should preserve the original spec with revision
    assert args.specs[0].raw == ".#test@HEAD~1"
    assert args.specs[1].raw == ".#test@HEAD"
