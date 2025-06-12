#!/usr/bin/env python3
"""Tests for derivation specification classes."""

from pathlib import Path

import pytest

from nix_hyperfine.parser import parse_derivation_spec
from nix_hyperfine.specs import AttributeSpec, FileSpec, FlakeSpec


def test_file_spec_simple_derivation(tmp_path: Path) -> None:
    """Test FileSpec with a simple .nix file."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    derivation {
      name = "test-derivation";
      system = builtins.currentSystem;
      builder = "/bin/sh";
      args = [ "-c" "echo 'Hello from test' > $out" ];
    }
    """)

    spec = FileSpec(raw=f"-f {nix_file}", file_path=str(nix_file), attribute=None)

    # Test getting derivation path
    drv_path = spec.get_derivation_path()
    assert drv_path.endswith(".drv")
    assert "/nix/store/" in drv_path

    # Test building - just verify it doesn't throw
    spec.build()

    # In sandbox environment, building is sufficient test


def test_file_spec_with_attribute(tmp_path: Path) -> None:
    """Test FileSpec with attribute selection."""
    nix_file = tmp_path / "test.nix"
    nix_file.write_text("""
    {
      fast = derivation {
        name = "fast-build";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo fast > $out" ];
      };
      slow = derivation {
        name = "slow-build";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "sleep 0.1; echo slow > $out" ];
      };
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


def test_flake_spec_local_flake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test FlakeSpec with a local flake."""
    flake_path = tmp_path / "flake.nix"
    flake_path.write_text("""
    {
      outputs = { self }:
      let
        system = "x86_64-linux";
      in {
        packages.${system}.default = derivation {
          name = "test-flake";
          inherit system;
          builder = "/bin/sh";
          args = [ "-c" "echo 'Hello from flake' > $out" ];
        };
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


def test_attribute_spec_with_nix_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AttributeSpec with a nix file that has attributes."""
    nix_file = tmp_path / "default.nix"
    nix_file.write_text("""
    {
      test-attr = derivation {
        name = "test-attr";
        system = builtins.currentSystem;
        builder = "/bin/sh";
        args = [ "-c" "echo 'test attribute' > $out" ];
      };
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
