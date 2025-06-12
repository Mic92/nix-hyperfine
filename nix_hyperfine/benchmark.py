"""Benchmarking functionality."""

import subprocess
import tempfile
from enum import Enum, auto
from pathlib import Path

from .dependencies import ensure_built
from .exceptions import HyperfineError
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


def _get_build_command(spec: DerivationSpec, out_link: Path | None = None) -> str:
    """Get the nix build command for a spec."""
    match spec:
        case FlakeSpec(flake_ref=flake_ref, attribute=attribute):
            out_link_arg = f" --out-link {out_link}" if out_link else ""
            return (
                f"nix --extra-experimental-features 'nix-command flakes' build "
                f"{flake_ref}#{attribute} --rebuild{out_link_arg}"
            )
        case FileSpec(file_path=file_path, attribute=attribute) if attribute:
            out_link_arg = f" -o {out_link}" if out_link else ""
            return f"nix-build{out_link_arg} {file_path} -A {attribute}"
        case FileSpec(file_path=file_path):
            out_link_arg = f" -o {out_link}" if out_link else ""
            return f"nix-build{out_link_arg} {file_path}"
        case AttributeSpec(attribute=attribute):
            out_link_arg = f" -o {out_link}" if out_link else ""
            return f"nix-build{out_link_arg} -A {attribute}"
        case _:
            msg = f"Unknown spec type: {type(spec)}"
            raise ValueError(msg)


def benchmark_eval(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """Benchmark evaluation of derivations.

    Args:
        specs: List of derivation specifications
        hyperfine_args: Additional arguments to pass to hyperfine

    """
    # Create a temporary directory for result symlinks
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Pre-build all derivations to ensure dependencies exist
        # This is faster than building dependencies separately
        ensure_built(specs, tmpdir_path)

        # Create eval commands with names
        hyperfine_cmd = ["hyperfine", *hyperfine_args]

        for spec in specs:
            # Add space before dash to prevent hyperfine from interpreting as flag
            name = f" {spec.raw}" if spec.raw.startswith("-") else spec.raw
            hyperfine_cmd.extend(["-n", name])
            hyperfine_cmd.append(_get_eval_command(spec))

        print(f"Running: {' '.join(hyperfine_cmd)}")
        try:
            subprocess.run(hyperfine_cmd, check=True)
        except subprocess.CalledProcessError as e:
            msg = f"Hyperfine failed with exit code {e.returncode}"
            raise HyperfineError(msg, returncode=e.returncode) from e


def benchmark_build(specs: list[DerivationSpec], hyperfine_args: list[str]) -> None:
    """Benchmark building of derivations.

    Args:
        specs: List of derivation specifications
        hyperfine_args: Additional arguments to pass to hyperfine

    """
    # Create a temporary directory for result symlinks
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Pre-build all derivations
        # This ensures all dependencies are available and is faster than
        # building dependencies separately
        ensure_built(specs, tmpdir_path)

        # Create build commands with names
        hyperfine_cmd = ["hyperfine", *hyperfine_args]

        for i, spec in enumerate(specs):
            # Add space before dash to prevent hyperfine from interpreting as flag
            name = f" {spec.raw}" if spec.raw.startswith("-") else spec.raw
            hyperfine_cmd.extend(["-n", name])
            # Create unique output link for each spec
            out_link = tmpdir_path / f"result-{i}"
            hyperfine_cmd.append(_get_build_command(spec, out_link))

        print(f"Running: {' '.join(hyperfine_cmd)}")
        subprocess.run(hyperfine_cmd, check=True)
