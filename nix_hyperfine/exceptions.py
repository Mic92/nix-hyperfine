"""Custom exceptions for nix-hyperfine."""


class NixError(Exception):
    """Exception raised for Nix command failures."""

    def __init__(self, message: str, returncode: int | None = None) -> None:
        """Initialize NixError with message and optional return code."""
        super().__init__(message)
        self.returncode = returncode


class HyperfineError(Exception):
    """Exception raised for Hyperfine-related errors."""

    def __init__(self, message: str, returncode: int | None = None) -> None:
        """Initialize HyperfineError with message and optional return code."""
        super().__init__(message)
        self.returncode = returncode
