"""Command execution utilities."""

import subprocess

from .exceptions import NixError


def run_command(
    cmd: list[str], capture_output: bool = True, check: bool = True
) -> subprocess.CompletedProcess[str]:
    """
    Run a command with proper error handling.

    Args:
        cmd: Command and arguments to run
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess with the result

    Raises:
        NixError: If command fails and check=True
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {' '.join(cmd)}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr.strip()}"
        raise NixError(error_msg) from e
