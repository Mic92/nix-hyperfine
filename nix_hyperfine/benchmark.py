"""Benchmarking functionality."""

import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto

from .dependencies import ensure_built
from .specs import AttributeSpec, DerivationSpec, FileSpec, FlakeSpec


class BenchmarkMode(Enum):
    BUILD = auto()
    EVAL = auto()


@dataclass
class BenchmarkConfig:
    """Configuration for benchmarking."""

    specs: list[DerivationSpec]
    mode: BenchmarkMode = BenchmarkMode.BUILD
    hyperfine_args: list[str] = field(default_factory=list)


def _get_eval_command(spec: DerivationSpec) -> str:
    """Get the nix evaluation command for a spec."""
    if isinstance(spec, FlakeSpec):
        return f"nix --extra-experimental-features 'nix-command flakes' eval --raw {spec.flake_ref}#{spec.attribute}.drvPath"
    elif isinstance(spec, FileSpec):
        if spec.attribute:
            return f"nix-instantiate {spec.file_path} -A {spec.attribute}"
        else:
            return f"nix-instantiate {spec.file_path}"
    elif isinstance(spec, AttributeSpec):
        return f"nix-instantiate -A {spec.attribute}"
    else:
        raise ValueError(f"Unknown spec type: {type(spec)}")


def _get_build_command(spec: DerivationSpec) -> str:
    """Get the nix build command for a spec."""
    if isinstance(spec, FlakeSpec):
        return f"nix --extra-experimental-features 'nix-command flakes' build {spec.flake_ref}#{spec.attribute} --rebuild"
    elif isinstance(spec, FileSpec):
        if spec.attribute:
            return f"nix-build {spec.file_path} -A {spec.attribute}"
        else:
            return f"nix-build {spec.file_path}"
    elif isinstance(spec, AttributeSpec):
        return f"nix-build -A {spec.attribute}"
    else:
        raise ValueError(f"Unknown spec type: {type(spec)}")


def benchmark_eval(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """
    Benchmark evaluation of derivations.

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
        hyperfine_cmd.extend(["-n", spec.raw])
        hyperfine_cmd.append(_get_eval_command(spec))

    print(f"Running: {' '.join(hyperfine_cmd)}")
    subprocess.run(hyperfine_cmd)


def benchmark_build(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """
    Benchmark building of derivations.

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
        hyperfine_cmd.extend(["-n", spec.raw])
        hyperfine_cmd.append(_get_build_command(spec))

    print(f"Running: {' '.join(hyperfine_cmd)}")
    subprocess.run(hyperfine_cmd)
