#!/usr/bin/env python3
"""Tests for the command module."""

import pytest

from nix_hyperfine.command import run_command
from nix_hyperfine.exceptions import NixError


def test_nix_error_on_failure() -> None:
    """Test that NixError is raised on command failure."""
    with pytest.raises(NixError) as exc_info:
        run_command(["nix-instantiate", "--eval", "-E", 'throw "test error"'])
    assert "Command failed" in str(exc_info.value)
