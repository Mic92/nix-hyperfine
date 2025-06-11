#!/usr/bin/env python3
"""Integration tests for nix-hyperfine."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from nix_hyperfine import (
    AttributeSpec,
    FileSpec,
    FlakeSpec,
    HyperfineError,
    NixError,
    build_dependencies,
    check_hyperfine,
    parse_derivation_spec,
    run_command,
)


class TestRunCommand:
    """Test the run_command function."""

    def test_successful_command(self):
        """Test running a successful command."""
        result = run_command(["echo", "hello"])
        assert result.returncode == 0
        assert result.stdout.strip() == "hello"

    def test_failed_command(self):
        """Test running a failing command."""
        with pytest.raises(NixError) as exc_info:
            run_command(["false"], check=True)
        assert "Command failed" in str(exc_info.value)

    def test_capture_output_false(self):
        """Test running command without capturing output."""
        result = run_command(["echo", "hello"], capture_output=False)
        assert result.returncode == 0
        assert result.stdout is None


class TestParseDerivationSpec:
    """Test derivation specification parsing."""

    def test_parse_flake_spec(self):
        """Test parsing flake references."""
        # Standard flake reference
        spec = parse_derivation_spec("nixpkgs#hello")
        assert isinstance(spec, FlakeSpec)
        assert spec.flake_ref == "nixpkgs"
        assert spec.attribute == "hello"
        assert spec.raw == "nixpkgs#hello"

        # Local flake reference
        spec = parse_derivation_spec(".#package")
        assert isinstance(spec, FlakeSpec)
        assert spec.flake_ref == "."
        assert spec.attribute == "package"

        # Empty flake ref (current directory)
        spec = parse_derivation_spec("#attr")
        assert isinstance(spec, FlakeSpec)
        assert spec.flake_ref == "."
        assert spec.attribute == "attr"

    def test_parse_file_spec(self):
        """Test parsing traditional nix file specifications."""
        # With attribute
        spec = parse_derivation_spec("-f file.nix -A hello")
        assert isinstance(spec, FileSpec)
        assert spec.file_path == "file.nix"
        assert spec.attribute == "hello"
        assert spec.raw == "-f file.nix -A hello"

        # File path ending with .nix
        spec = parse_derivation_spec("release.nix")
        assert isinstance(spec, FileSpec)
        assert spec.file_path == "release.nix"
        assert spec.attribute is None

        # Relative path
        spec = parse_derivation_spec("./default.nix")
        assert isinstance(spec, FileSpec)
        assert spec.file_path == "./default.nix"

        # Absolute path
        spec = parse_derivation_spec("/etc/nixos/configuration.nix")
        assert isinstance(spec, FileSpec)
        assert spec.file_path == "/etc/nixos/configuration.nix"

    def test_parse_attribute_spec(self):
        """Test parsing simple attribute specifications."""
        spec = parse_derivation_spec("hello")
        assert isinstance(spec, AttributeSpec)
        assert spec.attribute == "hello"
        assert spec.raw == "hello"


@pytest.mark.skipif(
    shutil.which("nix") is None,
    reason="Nix not available",
)
class TestNixIntegration:
    """Integration tests requiring a Nix installation."""

    def test_simple_nix_file_derivation(self):
        """Test building a simple derivation from a .nix file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".nix", delete=False) as f:
            f.write("""
            { pkgs ? import <nixpkgs> {} }:
            pkgs.runCommand "test-derivation" {} "echo 'Hello from test' > $out"
            """)
            nix_file = f.name

        try:
            # Test parsing
            spec = FileSpec(raw=f"-f {nix_file}", file_path=nix_file, attribute=None)

            # Test getting derivation path
            drv_path = spec.get_derivation_path()
            assert drv_path.endswith(".drv")
            assert "/nix/store/" in drv_path

            # Test building
            spec.build()

            # Verify the build by checking if output exists
            result = run_command(["nix-build", nix_file, "--no-out-link"], check=False)
            assert result.returncode == 0
            output_path = result.stdout.strip()
            assert Path(output_path).exists()

            # Read the output
            with open(output_path) as out:
                assert out.read().strip() == "Hello from test"

        finally:
            Path(nix_file).unlink()

    def test_flake_derivation(self):
        """Test building a derivation from a flake."""
        with tempfile.TemporaryDirectory() as tmpdir:
            flake_path = Path(tmpdir) / "flake.nix"
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
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Test parsing local flake reference
                spec = FlakeSpec(raw=".#default", flake_ref=".", attribute="default")

                # Test getting derivation path
                drv_path = spec.get_derivation_path()
                assert drv_path.endswith(".drv")
                assert "/nix/store/" in drv_path

                # Test building
                spec.build()

            finally:
                os.chdir(original_cwd)

    def test_build_dependencies_real(self):
        """Test building dependencies with a real derivation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".nix", delete=False) as f:
            # Create a derivation with a dependency
            f.write("""
            { pkgs ? import <nixpkgs> {} }:
            pkgs.runCommand "test-with-dep" {
              buildInputs = [ pkgs.hello ];
            } "
              hello --version > $out
              echo 'Additional content' >> $out
            "
            """)
            nix_file = f.name

        try:
            # Get the derivation path
            result = run_command(["nix-instantiate", nix_file])
            drv_path = result.stdout.strip()

            # Build dependencies
            build_dependencies(drv_path)

            # The hello dependency should now be built
            # Verify by checking if we can query its outputs
            result = run_command(["nix-store", "--query", "--requisites", drv_path], check=False)
            assert result.returncode == 0
            requisites = result.stdout.strip().split("\n")
            # Should have multiple requisites including hello
            assert len(requisites) > 1

        finally:
            Path(nix_file).unlink()

    def test_check_hyperfine_real(self):
        """Test actual hyperfine detection."""
        # This will use the real shutil.which
        try:
            check_hyperfine()
            # If we get here, hyperfine is installed
            result = subprocess.run(["hyperfine", "--version"], capture_output=True)
            assert result.returncode == 0
        except HyperfineError:
            # Hyperfine is not installed, which is fine for CI
            pass

    def test_end_to_end_simple(self):
        """Test a simple end-to-end scenario."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".nix", delete=False) as f:
            f.write("""
            { pkgs ? import <nixpkgs> {} }:
            {
              fast = pkgs.runCommand "fast-build" {} "echo fast > $out";
              slow = pkgs.runCommand "slow-build" {} "sleep 0.1; echo slow > $out";
            }
            """)
            nix_file = f.name

        try:
            # Parse specifications
            spec1 = parse_derivation_spec(f"-f {nix_file} -A fast")
            spec2 = parse_derivation_spec(f"-f {nix_file} -A slow")

            # Verify we can get derivation paths
            drv1 = spec1.get_derivation_path()
            drv2 = spec2.get_derivation_path()
            assert drv1 != drv2
            assert drv1.endswith(".drv")
            assert drv2.endswith(".drv")

            # Build both
            spec1.build()
            spec2.build()

        finally:
            Path(nix_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
