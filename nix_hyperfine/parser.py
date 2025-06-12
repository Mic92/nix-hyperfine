"""Command-line parsing utilities."""

import argparse
import subprocess
from pathlib import Path

from .benchmark import BenchmarkMode
from .exceptions import NixError
from .specs import AttributeSpec, DerivationSpec, FileSpec, FlakeSpec


def expand_git_revisions(spec: str) -> list[tuple[str, str | None]]:
    """
    Expand a spec with git revisions into multiple specs.

    Args:
        spec: The specification string possibly containing @revision

    Returns:
        List of (spec_without_revision, revision) tuples
    """
    # Check if spec contains @revision
    if "@" not in spec:
        return [(spec, None)]

    # Split at the last @ to handle cases like nixpkgs#hello@main
    parts = spec.rsplit("@", 1)
    base_spec = parts[0]
    revisions_str = parts[1]

    # Split multiple revisions by comma
    revisions = [rev.strip() for rev in revisions_str.split(",")]

    # Return list of specs with their revisions
    return [(base_spec, rev) for rev in revisions]


def create_git_revision_spec(base_spec: str, revision: str) -> str:
    """
    Create a spec that uses a git revision.

    This modifies the base spec to use a fetchGit store path.
    """
    # First resolve the revision to a commit hash
    git_dir = Path(".").resolve()
    try:
        # Get the full commit hash for the revision
        rev_parse_cmd = ["git", "-C", str(git_dir), "rev-parse", revision]
        rev_result = subprocess.run(rev_parse_cmd, capture_output=True, text=True, check=True)
        commit_hash = rev_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to resolve git revision '{revision}'"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        raise NixError(error_msg) from e

    # Get the git revision into the store
    fetch_expr = f"""
    let
      src = builtins.fetchGit {{
        url = "{git_dir}";
        rev = "{commit_hash}";
      }};
    in src
    """

    # Evaluate to get store path
    cmd = ["nix", "eval", "--impure", "--raw", "--expr", fetch_expr]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        store_path = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to fetch git revision '{revision}' (commit {commit_hash})"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        raise NixError(error_msg) from e

    # Modify the base spec to use the store path
    if "#" in base_spec and not base_spec.startswith("-"):
        # Flake reference - use store path as flake ref
        attribute = base_spec.split("#", 1)[1]
        return f"{store_path}#{attribute}"
    elif base_spec.startswith("-f "):
        # File spec - update the file path
        parts = base_spec[3:].split(" -A ", 1)
        file_path = parts[0].strip()
        attribute = parts[1].strip() if len(parts) > 1 else ""
        new_spec = f"-f {store_path}/{file_path}"
        if attribute:
            new_spec += f" -A {attribute}"
        return new_spec
    elif base_spec.endswith(".nix") or "/" in base_spec:
        # Direct file path
        return f"{store_path}/{base_spec}"
    else:
        # Simple attribute - assume default.nix
        return f"-f {store_path}/default.nix -A {base_spec}"


def parse_derivation_spec(spec: str) -> DerivationSpec:
    """
    Parse a derivation specification string into a typed spec.

    Args:
        spec: The specification string (e.g., "nixpkgs#hello", "-f file.nix -A attr", "hello")

    Returns:
        A parsed DerivationSpec subclass instance
    """
    # Check for flake reference (contains # but not a leading -)
    if "#" in spec and not spec.startswith("-"):
        # Flake reference like nixpkgs#hello
        parts = spec.split("#", 1)
        flake_ref = parts[0] if parts[0] else "."  # Empty flake ref means current directory
        return FlakeSpec(raw=spec, flake_ref=flake_ref, attribute=parts[1])

    # Check for file specification (-f file.nix [-A attr])
    if spec.startswith("-f "):
        parts = spec[3:].split(" -A ", 1)
        file_path = parts[0].strip()
        attribute = parts[1].strip() if len(parts) > 1 else None
        return FileSpec(raw=spec, file_path=file_path, attribute=attribute)

    # Check if it's a .nix file path
    if spec.endswith(".nix") or "/" in spec:
        return FileSpec(raw=spec, file_path=spec, attribute=None)

    # Simple attribute (just an attribute name)
    return AttributeSpec(raw=spec, attribute=spec)


def parse_args() -> tuple[list[DerivationSpec], BenchmarkMode, list[str]]:
    """
    Parse command-line arguments.

    Returns:
        Tuple of (derivation specs, benchmark mode, hyperfine args)
    """
    import sys

    # Split args at -- separator
    if "--" in sys.argv:
        sep_index = sys.argv.index("--")
        our_args = sys.argv[1:sep_index]
        hyperfine_args = sys.argv[sep_index + 1 :]
    else:
        our_args = sys.argv[1:]
        hyperfine_args = []

    parser = argparse.ArgumentParser(
        prog="nix-hyperfine",
        description="Benchmark Nix derivation builds with hyperfine",
        epilog="Any additional arguments after -- are passed directly to hyperfine",
    )

    # Mutually exclusive group for --build and --eval
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--build",
        action="store_true",
        help="Benchmark building derivations (default)",
    )
    mode_group.add_argument(
        "--eval",
        action="store_true",
        help="Benchmark evaluating derivations",
    )

    parser.add_argument(
        "derivations",
        nargs="+",
        help='Derivation specifications (e.g., "nixpkgs#hello", "-f file.nix -A attr", "hello", "hello@HEAD~1,main")',
    )

    # Parse our args only
    args = parser.parse_args(our_args)

    # Determine mode
    mode = BenchmarkMode.EVAL if args.eval else BenchmarkMode.BUILD

    # Expand git revisions and parse derivation specs
    specs = []
    for spec_str in args.derivations:
        expanded_specs = expand_git_revisions(spec_str)
        for base_spec, revision in expanded_specs:
            if revision:
                # Create a modified spec that uses the git revision
                modified_spec = create_git_revision_spec(base_spec, revision)
                parsed_spec = parse_derivation_spec(modified_spec)
                # Override the raw field to include the revision info
                parsed_spec.raw = f"{base_spec}@{revision}"
                specs.append(parsed_spec)
            else:
                # No revision, just parse normally
                specs.append(parse_derivation_spec(base_spec))

    return specs, mode, hyperfine_args
