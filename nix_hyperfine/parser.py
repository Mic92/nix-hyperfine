"""Command-line parsing utilities."""

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .benchmark import BenchmarkMode
from .command import run_command
from .exceptions import NixError
from .specs import AttributeSpec, DerivationSpec, FileSpec, FlakeSpec


@dataclass
class ParsedArgs:
    """Parsed command-line arguments."""

    specs: list[DerivationSpec]
    mode: BenchmarkMode
    hyperfine_args: list[str]


@dataclass
class ExpandedSpec:
    """An expanded derivation spec with optional git revision."""

    base_spec: str
    revision: str | None = None


def expand_git_revisions(spec: str) -> list[ExpandedSpec]:
    """Expand a spec with git revisions into multiple specs.

    Args:
        spec: The specification string possibly containing @revision

    Returns:
        List of ExpandedSpec instances

    """
    # Check if spec contains @revision
    if "@" not in spec:
        return [ExpandedSpec(base_spec=spec, revision=None)]

    # Split at the last @ to handle cases like nixpkgs#hello@main
    parts = spec.rsplit("@", 1)
    base_spec = parts[0]
    revisions_str = parts[1]

    # Split multiple revisions by comma
    revisions = [rev.strip() for rev in revisions_str.split(",")]

    # Return list of specs with their revisions
    return [ExpandedSpec(base_spec=base_spec, revision=rev) for rev in revisions]


def create_git_revision_spec(base_spec: str, revision: str) -> str:
    """Create a spec that uses a git revision.

    This modifies the base spec to use a fetchGit store path.
    """
    # First resolve the revision to a commit hash
    git_dir = Path.cwd()
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
        result = run_command(cmd, capture_output=True, check=True)
        store_path = result.stdout.strip()
    except NixError as e:
        msg = f"Failed to fetch git revision '{revision}' (commit {commit_hash}): {e}"
        raise NixError(
            msg,
        ) from e

    # Modify the base spec to use the store path
    match base_spec:
        case spec if "#" in spec and not spec.startswith("-"):
            # Flake reference - use store path as flake ref
            attribute = spec.split("#", 1)[1]
            return f"{store_path}#{attribute}"
        case spec if spec.startswith("-f "):
            # File spec - update the file path
            parts = spec[3:].split(" -A ", 1)
            file_path = parts[0].strip()
            attribute = parts[1].strip() if len(parts) > 1 else ""
            new_spec = f"-f {store_path}/{file_path}"
            if attribute:
                new_spec += f" -A {attribute}"
            return new_spec
        case spec if spec.endswith(".nix") or "/" in spec:
            # Direct file path
            return f"{store_path}/{spec}"
        case _:
            # Simple attribute - assume default.nix
            return f"-f {store_path}/default.nix -A {base_spec}"


def parse_derivation_spec(spec: str) -> DerivationSpec:
    """Parse a derivation specification string into a typed spec.

    Args:
        spec: The specification string (e.g., "nixpkgs#hello", "-f file.nix -A attr", "hello")

    Returns:
        A parsed DerivationSpec subclass instance

    """
    match spec:
        case s if "#" in s and not s.startswith("-"):
            # Flake reference like nixpkgs#hello
            parts = s.split("#", 1)
            flake_ref = parts[0] if parts[0] else "."  # Empty flake ref means current directory
            return FlakeSpec(raw=spec, flake_ref=flake_ref, attribute=parts[1])
        case s if s.startswith("-f "):
            # File specification (-f file.nix [-A attr])
            parts = s[3:].split(" -A ", 1)
            file_path = parts[0].strip()
            attribute = parts[1].strip() if len(parts) > 1 else None
            return FileSpec(raw=spec, file_path=file_path, attribute=attribute)
        case s if s.endswith(".nix") or "/" in s:
            # Direct .nix file path
            return FileSpec(raw=spec, file_path=s, attribute=None)
        case _:
            # Simple attribute (just an attribute name)
            return AttributeSpec(raw=spec, attribute=spec)


def parse_args(argv: list[str] | None = None) -> ParsedArgs:
    """Parse command-line arguments.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        ParsedArgs containing derivation specs, benchmark mode, and hyperfine args

    """
    import sys

    if argv is None:
        argv = sys.argv

    # Split args at -- separator
    if "--" in argv:
        sep_index = argv.index("--")
        our_args = argv[1:sep_index]
        hyperfine_args = argv[sep_index + 1 :]
    else:
        our_args = argv[1:]
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
        for expanded in expanded_specs:
            if expanded.revision:
                # Create a modified spec that uses the git revision
                modified_spec = create_git_revision_spec(expanded.base_spec, expanded.revision)
                parsed_spec = parse_derivation_spec(modified_spec)
                # Override the raw field to include the revision info
                parsed_spec.raw = f"{expanded.base_spec}@{expanded.revision}"
                specs.append(parsed_spec)
            else:
                # No revision, just parse normally
                specs.append(parse_derivation_spec(expanded.base_spec))

    return ParsedArgs(specs=specs, mode=mode, hyperfine_args=hyperfine_args)
