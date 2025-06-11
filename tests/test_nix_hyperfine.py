#!/usr/bin/env python3
"""Integration tests for nix-hyperfine."""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from nix_hyperfine import (
    AttributeSpec,
    BenchmarkConfig,
    DerivationSpec,
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


class TestDerivationSpecs:
    """Test DerivationSpec subclasses."""

    @patch('nix_hyperfine.run_command')
    def test_flake_spec_get_derivation_path(self, mock_run):
        """Test FlakeSpec.get_derivation_path."""
        # Test successful path-info
        mock_run.return_value = Mock(
            returncode=0,
            stdout="/nix/store/abc123-hello.drv\n"
        )
        
        spec = FlakeSpec(raw="nixpkgs#hello", flake_ref="nixpkgs", attribute="hello")
        drv_path = spec.get_derivation_path()
        
        assert drv_path == "/nix/store/abc123-hello.drv"
        mock_run.assert_called_once_with(
            ["nix", "path-info", "--derivation", "nixpkgs#hello"],
            check=False
        )

    @patch('nix_hyperfine.run_command')
    def test_flake_spec_build(self, mock_run):
        """Test FlakeSpec.build."""
        mock_run.return_value = Mock(returncode=0)
        
        spec = FlakeSpec(raw="nixpkgs#hello", flake_ref="nixpkgs", attribute="hello")
        spec.build()
        
        mock_run.assert_called_once_with(
            ["nix", "build", "nixpkgs#hello", "--no-link", "--log-format", "bar-with-logs"],
            capture_output=False
        )

    @patch('nix_hyperfine.run_command')
    def test_file_spec_get_derivation_path(self, mock_run):
        """Test FileSpec.get_derivation_path."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="/nix/store/xyz789-package.drv\n"
        )
        
        spec = FileSpec(raw="-f file.nix -A pkg", file_path="file.nix", attribute="pkg")
        drv_path = spec.get_derivation_path()
        
        assert drv_path == "/nix/store/xyz789-package.drv"
        mock_run.assert_called_once_with(
            ["nix-instantiate", "file.nix", "-A", "pkg"],
            check=False
        )

    @patch('nix_hyperfine.run_command')
    def test_attribute_spec_fallback(self, mock_run):
        """Test AttributeSpec fallback mechanism."""
        # First call fails (flake), second succeeds (nix-instantiate)
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),
            Mock(returncode=0, stdout="/nix/store/def456-hello.drv\n")
        ]
        
        spec = AttributeSpec(raw="hello", attribute="hello")
        drv_path = spec.get_derivation_path()
        
        assert drv_path == "/nix/store/def456-hello.drv"
        assert mock_run.call_count == 2


class TestBuildDependencies:
    """Test build_dependencies function."""

    @patch('nix_hyperfine.run_command')
    def test_build_dependencies_batching(self, mock_run):
        """Test that dependencies are built in batches."""
        # Generate many dependencies
        deps = [f"/nix/store/dep{i}.drv" for i in range(250)]
        drv_path = "/nix/store/main.drv"
        all_reqs = [drv_path] + deps
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="\n".join(all_reqs)
        )
        
        build_dependencies(drv_path, batch_size=100)
        
        # Should be called once for query, then 3 times for building (250 deps / 100 batch size)
        assert mock_run.call_count == 4
        
        # Check first call was the query
        assert mock_run.call_args_list[0][0][0][:3] == ["nix-store", "--query", "--requisites"]
        
        # Check subsequent calls were realizes in batches
        for i in range(1, 4):
            call_args = mock_run.call_args_list[i][0][0]
            assert call_args[:3] == ["nix-store", "--realize", "--quiet"]
            # Verify batch sizes
            if i < 3:
                assert len(call_args) == 103  # 3 command parts + 100 deps
            else:
                assert len(call_args) == 53   # 3 command parts + 50 remaining deps


class TestCheckHyperfine:
    """Test hyperfine availability checking."""

    @patch('shutil.which')
    def test_hyperfine_found(self, mock_which):
        """Test when hyperfine is found."""
        mock_which.return_value = "/usr/bin/hyperfine"
        check_hyperfine()  # Should not raise

    @patch('shutil.which')
    def test_hyperfine_not_found(self, mock_which):
        """Test when hyperfine is not found."""
        mock_which.return_value = None
        with pytest.raises(HyperfineError) as exc_info:
            check_hyperfine()
        assert "hyperfine not found" in str(exc_info.value)


class TestIntegration:
    """Integration tests with actual Nix commands."""

    @pytest.mark.skipif(
        subprocess.run(["which", "nix"], capture_output=True).returncode != 0,
        reason="Nix not available"
    )
    def test_simple_derivation(self):
        """Test with a simple derivation that should exist."""
        # This test requires a working Nix installation
        # We'll use a minimal derivation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nix', delete=False) as f:
            f.write('''
            { pkgs ? import <nixpkgs> {} }:
            pkgs.runCommand "test-derivation" {} "echo test > $out"
            ''')
            nix_file = f.name

        try:
            spec = FileSpec(raw=f"-f {nix_file}", file_path=nix_file, attribute=None)
            drv_path = spec.get_derivation_path()
            assert drv_path.endswith('.drv')
            assert '/nix/store/' in drv_path
        finally:
            Path(nix_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])