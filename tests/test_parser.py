#!/usr/bin/env python3
"""Tests for the parser module."""

import sys

import pytest

from nix_hyperfine.benchmark import BenchmarkMode
from nix_hyperfine.parser import expand_git_revisions, parse_args, parse_derivation_spec
from nix_hyperfine.specs import AttributeSpec, FileSpec, FlakeSpec


def test_parse_flake_spec() -> None:
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


def test_parse_file_spec() -> None:
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


def test_parse_attribute_spec() -> None:
    """Test parsing simple attribute specifications."""
    spec = parse_derivation_spec("hello")
    assert isinstance(spec, AttributeSpec)
    assert spec.attribute == "hello"
    assert spec.raw == "hello"


def test_parse_args_default_build_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that build mode is default."""
    monkeypatch.setattr(sys, "argv", ["nix-hyperfine", "hello"])
    args = parse_args()

    assert len(args.specs) == 1
    assert isinstance(args.specs[0], AttributeSpec)
    assert args.specs[0].attribute == "hello"
    assert args.mode == BenchmarkMode.BUILD
    assert args.hyperfine_args == []


def test_parse_args_eval_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test --eval flag."""
    monkeypatch.setattr(sys, "argv", ["nix-hyperfine", "--eval", "hello"])
    args = parse_args()

    assert len(args.specs) == 1
    assert args.mode == BenchmarkMode.EVAL


def test_parse_args_build_mode_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test --build flag."""
    monkeypatch.setattr(sys, "argv", ["nix-hyperfine", "--build", "hello"])
    args = parse_args()

    assert len(args.specs) == 1
    assert args.mode == BenchmarkMode.BUILD


def test_parse_args_with_hyperfine_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test passing arguments to hyperfine."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["nix-hyperfine", "hello", "--", "--runs", "5", "--warmup", "2"],
    )
    args = parse_args()

    assert len(args.specs) == 1
    assert args.hyperfine_args == ["--runs", "5", "--warmup", "2"]


def test_parse_args_multiple_derivations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test multiple derivation specifications."""
    monkeypatch.setattr(sys, "argv", ["nix-hyperfine", "hello", "cowsay", "nixpkgs#lolcat"])
    args = parse_args()

    assert len(args.specs) == 3
    assert isinstance(args.specs[0], AttributeSpec)
    assert isinstance(args.specs[1], AttributeSpec)
    assert isinstance(args.specs[2], FlakeSpec)


def test_parse_args_eval_with_hyperfine_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test --eval with hyperfine arguments."""
    monkeypatch.setattr(sys, "argv", ["nix-hyperfine", "--eval", "hello", "--", "--runs", "3"])
    args = parse_args()

    assert args.mode == BenchmarkMode.EVAL
    assert args.hyperfine_args == ["--runs", "3"]


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
