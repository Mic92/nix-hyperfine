"""Benchmarking functionality."""

import subprocess
from enum import Enum, auto

from .dependencies import ensure_built
from .specs import AttributeSpec, DerivationSpec, FileSpec, FlakeSpec


class BenchmarkMode(Enum):
    """Enumeration of benchmark modes."""

    BUILD = auto()
    EVAL = auto()


def _get_eval_command(spec: DerivationSpec) -> str:
    """Get the nix evaluation command for a spec."""
    match spec:
        case FlakeSpec(flake_ref=flake_ref, attribute=attribute):
            return (
                f"nix --extra-experimental-features 'nix-command flakes' eval --raw --no-eval-cache "
                f"{flake_ref}#{attribute}.drvPath"
            )
        case FileSpec(file_path=file_path, attribute=attribute) if attribute:
            return f"nix-instantiate {file_path} -A {attribute}"
        case FileSpec(file_path=file_path):
            return f"nix-instantiate {file_path}"
        case AttributeSpec(attribute=attribute):
            return f"nix-instantiate -A {attribute}"
        case _:
            msg = f"Unknown spec type: {type(spec)}"
            raise ValueError(msg)


def _get_build_command(spec: DerivationSpec) -> str:
    """Get the nix build command for a spec."""
    match spec:
        case FlakeSpec(flake_ref=flake_ref, attribute=attribute):
            return (
                f"nix --extra-experimental-features 'nix-command flakes' build "
                f"{flake_ref}#{attribute} --rebuild"
            )
        case FileSpec(file_path=file_path, attribute=attribute) if attribute:
            return f"nix-build {file_path} -A {attribute}"
        case FileSpec(file_path=file_path):
            return f"nix-build {file_path}"
        case AttributeSpec(attribute=attribute):
            return f"nix-build -A {attribute}"
        case _:
            msg = f"Unknown spec type: {type(spec)}"
            raise ValueError(msg)


def benchmark_eval(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """Benchmark evaluation of derivations.

    Args:
        specs: List of derivation specifications
        hyperfine_args: Additional arguments to pass to hyperfine

    """
    # Pre-build all derivations to ensure dependencies exist
    # This is faster than building dependencies separately
    ensure_built(specs)

    # Create eval commands with names
    hyperfine_cmd = ["hyperfine", *hyperfine_args]

    for spec in specs:
        # Add space before dash to prevent hyperfine from interpreting as flag
        name = f" {spec.raw}" if spec.raw.startswith("-") else spec.raw
        hyperfine_cmd.extend(["-n", name])
        hyperfine_cmd.append(_get_eval_command(spec))

    print(f"Running: {' '.join(hyperfine_cmd)}")
    subprocess.run(hyperfine_cmd, check=True)


def benchmark_build(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """Benchmark building of derivations.

    Args:
        specs: List of derivation specifications
        hyperfine_args: Additional arguments to pass to hyperfine

    """
    # Pre-build all derivations
    # This ensures all dependencies are available and is faster than
    # building dependencies separately
    ensure_built(specs)

    # Create build commands with names
    hyperfine_cmd = ["hyperfine", *hyperfine_args]

    for spec in specs:
        # Add space before dash to prevent hyperfine from interpreting as flag
        name = f" {spec.raw}" if spec.raw.startswith("-") else spec.raw
        hyperfine_cmd.extend(["-n", name])
        hyperfine_cmd.append(_get_build_command(spec))

    print(f"Running: {' '.join(hyperfine_cmd)}")
    subprocess.run(hyperfine_cmd, check=True)
