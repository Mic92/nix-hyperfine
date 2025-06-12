"""Pytest configuration for nix-hyperfine tests."""

import pytest


@pytest.fixture
def git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up git environment variables for testing."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
