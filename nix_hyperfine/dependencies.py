"""Dependency checking and building utilities."""

import shutil
import time
from pathlib import Path

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


def ensure_built(specs: list[DerivationSpec], tmpdir: Path | None = None) -> None:
    """Ensure all derivations are built before benchmarking.

    Args:
        specs: List of derivation specifications to build
        tmpdir: Optional temporary directory for output links

    """
    for i, spec in enumerate(specs):
        print(info(f"Pre-building {spec.raw}..."))
        build_start = time.time()
        if tmpdir:
            out_link = tmpdir / f"prebuild-{i}"
            spec.build(capture_output=True, out_link=out_link)
        else:
            spec.build(capture_output=True)
        build_time = time.time() - build_start
        print(dim(f"  Pre-build completed in {build_time:.2f}s"))
