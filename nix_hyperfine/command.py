"""Command execution utilities."""

import subprocess

from .exceptions import NixError


def add_experimental_flags(cmd: list[str]) -> list[str]:
    """Add experimental flags to nix commands that need them.

    Args:
        cmd: Command list to potentially modify

    Returns:
        Modified command list with experimental flags if needed

    """
    if not cmd:
        return cmd

    # Commands that need experimental features
    if cmd[0] == "nix" and len(cmd) > 1:
        # Add experimental features after the nix command but before subcommand
        return [cmd[0], "--extra-experimental-features", "nix-command flakes"] + cmd[1:]

    return cmd


def run_command(
    cmd: list[str],
    capture_output: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command with proper error handling.

    Args:
        cmd: Command and arguments to run
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess with the result

    Raises:
        NixError: If command fails and check=True

    """
    # Add experimental flags if needed
    cmd = add_experimental_flags(cmd)

    try:
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=check,
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {' '.join(cmd)}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr.strip()}"
        raise NixError(error_msg, returncode=e.returncode) from e
