"""Dependency checking and building utilities."""

import shutil
import sys

from .command import run_command
from .exceptions import HyperfineError
from .specs import DerivationSpec


def check_hyperfine() -> None:
    """Check if hyperfine is available."""
    if not shutil.which("hyperfine"):
        print("Error: hyperfine not found in PATH")
        print("Install it with: nix-env -iA nixpkgs.hyperfine")
        raise HyperfineError("hyperfine not found")


def build_dependencies(drv_path: str) -> None:
    """
    Build all dependencies for a derivation.

    Args:
        drv_path: Path to the .drv file
    """
    print(f"Getting dependencies for {drv_path}...")
    cmd = ["nix-store", "--query", "--requisites", drv_path]
    result = run_command(cmd)

    deps = [d for d in result.stdout.strip().split("\n") if d.endswith(".drv")]
    if not deps:
        return

    print(f"Building {len(deps)} dependencies...")
    # Batch the dependencies to avoid command line length limits
    batch_size = 100
    for i in range(0, len(deps), batch_size):
        batch = deps[i : i + batch_size]
        build_cmd = ["nix-store", "--realise", *batch]
        try:
            run_command(build_cmd)
        except Exception as e:
            print(f"Warning: Failed to build some dependencies: {e}", file=sys.stderr)
            # Continue anyway, nix build will fail if critical deps are missing


def ensure_built(specs: list[DerivationSpec]) -> None:
    """
    Ensure all derivations are built before benchmarking.

    Args:
        specs: List of derivation specifications to build
    """
    for spec in specs:
        print(f"Pre-building {spec.raw}...")
        spec.build(capture_output=True)
