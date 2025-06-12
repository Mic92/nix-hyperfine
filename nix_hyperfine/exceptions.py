"""Custom exceptions for nix-hyperfine."""


class NixError(Exception):
    """Exception raised for Nix command failures."""

    pass


class HyperfineError(Exception):
    """Exception raised for Hyperfine-related errors."""

    pass
