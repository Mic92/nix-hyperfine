"""Dependency checking and building utilities."""

import shutil
import time

from .colors import dim, error, info
from .exceptions import HyperfineError
from .specs import DerivationSpec


def check_hyperfine() -> None:
    """Check if hyperfine is available."""
    if not shutil.which("hyperfine"):
        print(error("Error: hyperfine not found in PATH"))
        print(info("Install it with: nix-env -iA nixpkgs.hyperfine"))
        msg = "hyperfine not found"
        raise HyperfineError(msg)


def ensure_built(specs: list[DerivationSpec]) -> None:
    """Ensure all derivations are built before benchmarking.

    Args:
        specs: List of derivation specifications to build

    """
    for spec in specs:
        print(info(f"Pre-building {spec.raw}..."))
        build_start = time.time()
        spec.build(capture_output=True)
        build_time = time.time() - build_start
        print(dim(f"  Pre-build completed in {build_time:.2f}s"))
