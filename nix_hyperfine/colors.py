"""Terminal color utilities."""

import os
import sys


class Colors:
    """ANSI color codes."""

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def supports_color() -> bool:
    """Check if terminal supports color output."""
    # Check NO_COLOR environment variable
    if os.environ.get("NO_COLOR"):
        return False

    # Check if stdout is a TTY
    if not sys.stdout.isatty():
        return False

    # Check TERM environment variable
    term = os.environ.get("TERM", "")
    return term not in ("dumb", "")


def colorize(text: str, color: str) -> str:
    """Colorize text if colors are supported."""
    if supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


def error(text: str) -> str:
    """Format error text with red color."""
    return colorize(text, Colors.RED)


def warning(text: str) -> str:
    """Format warning text with yellow color."""
    return colorize(text, Colors.YELLOW)


def info(text: str) -> str:
    """Format info text with blue color."""
    return colorize(text, Colors.BLUE)


def dim(text: str) -> str:
    """Format text as dim."""
    return colorize(text, Colors.DIM)
