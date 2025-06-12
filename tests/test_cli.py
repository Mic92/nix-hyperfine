#!/usr/bin/env python3
"""Tests for command-line interface."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(
    shutil.which("nix") is None or shutil.which("hyperfine") is None,
    reason="Nix or hyperfine not available",
)
def test_command_line_invocation(tmp_path: Path) -> None:
    """Test invoking nix-hyperfine via command line."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    { pkgs ? import <nixpkgs> {} }:
    pkgs.runCommand "test-cli" {} "echo 'cli test' > $out"
    """)

    # Test basic invocation
    result = subprocess.run(
        ["python", "-m", "nix_hyperfine", f"-f {nix_file}", "--", "--runs", "1"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Benchmark" in result.stdout or "hyperfine" in result.stdout.lower()


@pytest.mark.skipif(
    shutil.which("nix") is None or shutil.which("hyperfine") is None,
    reason="Nix or hyperfine not available",
)
def test_cli_eval_mode(tmp_path: Path) -> None:
    """Test CLI with --eval flag."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    { pkgs ? import <nixpkgs> {} }:
    pkgs.runCommand "test-eval-cli" {} "echo 'eval cli test' > $out"
    """)

    # Test eval mode invocation
    result = subprocess.run(
        ["python", "-m", "nix_hyperfine", "--eval", f"-f {nix_file}", "--", "--runs", "1"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "nix-instantiate" in result.stdout or "eval" in result.stdout.lower()


def test_cli_help() -> None:
    """Test CLI help output."""
    result = subprocess.run(
        ["python", "-m", "nix_hyperfine", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Benchmark Nix derivation builds with hyperfine" in result.stdout
    assert "--build" in result.stdout
    assert "--eval" in result.stdout
    assert "derivations" in result.stdout
