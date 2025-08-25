"""Pytest configuration for nix-hyperfine tests."""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up git environment variables for testing."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")


@pytest.fixture(autouse=True)
def nix_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Set up Nix environment for testing to avoid store conflicts."""
    # We're in a sandboxed environment, set up alternative paths
    # Use /tmp for Nix store to avoid sandbox-build-dir conflicts
    # Create a unique directory in /tmp for the Nix store
    nix_root = Path(tempfile.mkdtemp(prefix="nix-test-"))

    nix_store_dir = nix_root / "store"
    nix_store_dir.mkdir(parents=True, exist_ok=True)

    nix_var_dir = nix_root / "var"
    nix_var_dir.mkdir(parents=True, exist_ok=True)

    nix_log_dir = nix_var_dir / "log" / "nix" / "drvs"
    nix_log_dir.mkdir(parents=True, exist_ok=True)

    nix_state_dir = nix_root / "state"
    nix_state_dir.mkdir(exist_ok=True)

    # Set NIX environment variables to use our temp directories
    monkeypatch.setenv("NIX_STORE_DIR", str(nix_store_dir))
    monkeypatch.setenv("NIX_DATA_DIR", str(nix_root / "share"))
    monkeypatch.setenv("NIX_LOG_DIR", str(nix_var_dir / "log" / "nix"))
    monkeypatch.setenv("NIX_STATE_DIR", str(nix_state_dir))
    monkeypatch.setenv("NIX_CONF_DIR", str(nix_root / "etc"))

    # Set cache directory per test to avoid conflicts
    nix_cache_dir = nix_root / "cache"
    nix_cache_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("XDG_CACHE_HOME", str(nix_cache_dir))

    # Use pytest's tmp_path for temporary directories
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir(exist_ok=True)
    monkeypatch.setenv("TMPDIR", str(tmpdir))
    monkeypatch.setenv("TMP", str(tmpdir))
    monkeypatch.setenv("TEMP", str(tmpdir))

    # Configure Nix for sandbox mode without network access
    nix_config = """
substituters =
connect-timeout = 0
sandbox = false
"""
    monkeypatch.setenv("NIX_CONFIG", nix_config.strip())

    # Disable sandbox for tests
    monkeypatch.setenv("_NIX_TEST_NO_SANDBOX", "1")

    # Unset NIX_REMOTE to avoid daemon mode
    monkeypatch.delenv("NIX_REMOTE", raising=False)

    # Clean up the nix root directory when the test is done
    try:
        yield
    finally:
        shutil.rmtree(nix_root, ignore_errors=True)
