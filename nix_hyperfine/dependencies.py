"""Dependency checking and building utilities."""

import shutil
import subprocess
import sys
import time

from .colors import dim, error, info, warning
from .command import run_command
from .exceptions import HyperfineError
from .specs import DerivationSpec


def check_hyperfine() -> None:
    """Check if hyperfine is available."""
    if not shutil.which("hyperfine"):
        print(error("Error: hyperfine not found in PATH"))
        print(info("Install it with: nix-env -iA nixpkgs.hyperfine"))
        msg = "hyperfine not found"
        raise HyperfineError(msg)


def build_dependencies(drv_path: str) -> None:
    """Build all dependencies for a derivation.

    Args:
        drv_path: Path to the .drv file

    """
    start_time = time.time()
    print(info(f"Getting dependencies for {drv_path}..."))
    cmd = ["nix-store", "--query", "--requisites", drv_path]
    query_start = time.time()
    result = run_command(cmd)
    query_time = time.time() - query_start
    print(dim(f"  Dependency query took {query_time:.2f}s"))

    deps = [d for d in result.stdout.strip().split("\n") if d.endswith(".drv")]
    if not deps:
        return

    print(info(f"Building {len(deps)} dependencies..."))
    # Batch the dependencies to avoid command line length limits
    batch_size = 100
    total_batches = (len(deps) + batch_size - 1) // batch_size

    for i in range(0, len(deps), batch_size):
        batch = deps[i : i + batch_size]
        batch_num = i // batch_size + 1
        print(dim(f"  Building batch {batch_num}/{total_batches} ({len(batch)} dependencies)..."))
        batch_start = time.time()
        build_cmd = ["nix-store", "--realise", *batch]
        try:
            run_command(build_cmd)
            batch_time = time.time() - batch_start
            print(dim(f"  Batch {batch_num} completed in {batch_time:.2f}s"))
        except (OSError, subprocess.CalledProcessError) as e:
            print(warning(f"Warning: Failed to build some dependencies: {e}"), file=sys.stderr)
            # Continue anyway, nix build will fail if critical deps are missing

    total_time = time.time() - start_time
    print(info(f"Total dependency building took {total_time:.2f}s"))


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
