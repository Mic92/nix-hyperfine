#!/usr/bin/env python3
"""Tests for benchmarking functionality."""

import shutil
from pathlib import Path

import pytest

from nix_hyperfine.benchmark import benchmark_build, benchmark_eval
from nix_hyperfine.parser import parse_derivation_spec


@pytest.mark.skipif(
    shutil.which("nix") is None or shutil.which("hyperfine") is None,
    reason="Nix or hyperfine not available",
)
def test_benchmark_eval_mode(tmp_path: Path) -> None:
    """Test benchmark_eval function."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    derivation {
      name = "test-eval";
      system = builtins.currentSystem;
      builder = "/bin/sh";
      args = [ "-c" "echo 'test' > $out" ];
    }
    """)

    spec = parse_derivation_spec(f"-f {nix_file}")

    # Run benchmark_eval - should complete without error
    benchmark_eval([spec], ["--runs", "1"])


@pytest.mark.skipif(
    shutil.which("nix") is None or shutil.which("hyperfine") is None,
    reason="Nix or hyperfine not available",
)
def test_benchmark_build_mode(tmp_path: Path) -> None:
    """Test benchmark_build function."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    derivation {
      name = "test-build";
      system = builtins.currentSystem;
      builder = "/bin/sh";
      args = [ "-c" "echo 'test' > $out" ];
    }
    """)

    spec = parse_derivation_spec(f"-f {nix_file}")

    # Run benchmark_build - should complete without error
    benchmark_build([spec], ["--runs", "1"])


@pytest.mark.skipif(
    shutil.which("nix") is None or shutil.which("hyperfine") is None,
    reason="Nix or hyperfine not available",
)
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
