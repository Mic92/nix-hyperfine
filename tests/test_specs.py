#!/usr/bin/env python3
"""Tests for derivation specification classes."""

import shutil
from pathlib import Path

import pytest

from nix_hyperfine.command import run_command
from nix_hyperfine.parser import parse_derivation_spec
from nix_hyperfine.specs import AttributeSpec, FileSpec, FlakeSpec


@pytest.mark.skipif(
    shutil.which("nix") is None,
    reason="Nix not available",
)
def test_file_spec_simple_derivation(tmp_path: Path) -> None:
    """Test FileSpec with a simple .nix file."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    { pkgs ? import <nixpkgs> {} }:
    pkgs.runCommand "test-derivation" {} "echo 'Hello from test' > $out"
    """)

    spec = FileSpec(raw=f"-f {nix_file}", file_path=str(nix_file), attribute=None)

    # Test getting derivation path
    drv_path = spec.get_derivation_path()
    assert drv_path.endswith(".drv")
    assert "/nix/store/" in drv_path

    # Test building
    spec.build()

    # Verify the build by checking if output exists
    result = run_command(["nix-build", str(nix_file), "--no-out-link"], check=False)
    assert result.returncode == 0
    output_path = result.stdout.strip()
    assert Path(output_path).exists()

    # Read the output
    with open(output_path) as out:
        assert out.read().strip() == "Hello from test"


@pytest.mark.skipif(
    shutil.which("nix") is None,
    reason="Nix not available",
)
def test_file_spec_with_attribute(tmp_path: Path) -> None:
    """Test FileSpec with attribute selection."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    { pkgs ? import <nixpkgs> {} }:
    {
      fast = pkgs.runCommand "fast-build" {} "echo fast > $out";
      slow = pkgs.runCommand "slow-build" {} "sleep 0.1; echo slow > $out";
    }
    """)

    # Parse specifications with attributes
    spec = parse_derivation_spec(f"-f {nix_file} -A fast")

    assert isinstance(spec, FileSpec)
    assert spec.file_path == str(nix_file)
    assert spec.attribute == "fast"

    # Verify we can get derivation path
    drv_path = spec.get_derivation_path()
    assert drv_path.endswith(".drv")
    assert "fast-build" in drv_path


@pytest.mark.skipif(
    shutil.which("nix") is None,
    reason="Nix not available",
)
def test_flake_spec_local_flake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test FlakeSpec with a local flake."""
    flake_path = tmp_path / "flake.nix"
    flake_path.write_text("""
    {
      outputs = { self, nixpkgs }: {
        packages.x86_64-linux.default =
          nixpkgs.legacyPackages.x86_64-linux.runCommand "test-flake" {}
            "echo 'Hello from flake' > $out";
      };
    }
    """)

    # Change to the temp directory
    monkeypatch.chdir(tmp_path)

    # Test parsing local flake reference
    spec = FlakeSpec(raw=".#default", flake_ref=".", attribute="default")

    # Test getting derivation path
    drv_path = spec.get_derivation_path()
    assert drv_path.endswith(".drv")
    assert "/nix/store/" in drv_path

    # Test building
    spec.build()


@pytest.mark.skipif(
    shutil.which("nix") is None,
    reason="Nix not available",
)
def test_attribute_spec_with_nix_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AttributeSpec with a nix file that has attributes."""
    nix_file = tmp_path / "default.nix"
    nix_file.write_text("""
    { pkgs ? import <nixpkgs> {} }:
    {
      test-attr = pkgs.runCommand "test-attr" {} "echo 'test attribute' > $out";
    }
    """)

    # Change to the temp directory so default.nix is found
    monkeypatch.chdir(tmp_path)

    spec = AttributeSpec(raw="test-attr", attribute="test-attr")

    # Test getting derivation path
    drv_path = spec.get_derivation_path()
    assert drv_path.endswith(".drv")
    assert "/nix/store/" in drv_path
    assert "test-attr" in drv_path
