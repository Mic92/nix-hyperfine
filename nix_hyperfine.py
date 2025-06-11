#!/usr/bin/env python3
"""nix-hyperfine: Wrapper around hyperfine for benchmarking nix builds.

Ensures all dependencies are built before benchmarking.
"""

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field


from abc import ABC, abstractmethod


class NixError(Exception):
    """Base exception for Nix-related errors."""
    pass


class HyperfineError(Exception):
    """Exception for hyperfine-related errors."""
    pass


def run_command(cmd: list[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result.

    Args:
        cmd: Command and arguments to run
        check: Whether to raise exception on non-zero exit
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess instance
    """
    try:
        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
    except subprocess.CalledProcessError as e:
        # Re-raise with more context
        raise NixError(f"Command failed: {' '.join(cmd)}\n{e.stderr}") from e


@dataclass
class DerivationSpec(ABC):
    """Base class for parsed derivation specifications."""
    raw: str  # Original specification string

    @abstractmethod
    def get_derivation_path(self) -> str:
        """Get the derivation path (.drv file)."""
        pass

    @abstractmethod
    def build(self, capture_output: bool = False) -> None:
        """Build the derivation."""
        pass


@dataclass
class FlakeSpec(DerivationSpec):
    """Flake reference specification (e.g., nixpkgs#hello)."""
    flake_ref: str
    attribute: str

    def get_derivation_path(self) -> str:
        """Get derivation path using nix path-info."""
        print(f"Instantiating {self.raw}...")

        # Try nix path-info first
        result = run_command(
            ["nix", "path-info", "--derivation", f"{self.flake_ref}#{self.attribute}"],
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            drv_path = result.stdout.strip()
        else:
            # Fallback to nix eval
            result = run_command(
                ["nix", "eval", "--raw", f"{self.flake_ref}#{self.attribute}.drvPath"],
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                drv_path = result.stdout.strip()
            else:
                raise NixError(f"Failed to get derivation path for {self.raw}")

        print(f"Derivation: {drv_path}")
        return drv_path

    def build(self, capture_output: bool = False) -> None:
        """Build using nix build."""
        build_cmd = [
            "nix", "build", f"{self.flake_ref}#{self.attribute}", "--no-link",
            "--log-format", "bar-with-logs"
        ]
        run_command(build_cmd, capture_output=capture_output)


@dataclass
class FileSpec(DerivationSpec):
    """Traditional nix file specification (e.g., -f file.nix -A attr)."""
    file_path: str
    attribute: str | None = None

    def get_derivation_path(self) -> str:
        """Get derivation path using nix-instantiate."""
        print(f"Instantiating {self.raw}...")

        if self.attribute:
            cmd = ["nix-instantiate", self.file_path, "-A", self.attribute]
        else:
            cmd = ["nix-instantiate", self.file_path]

        result = run_command(cmd, check=False)

        if result.returncode == 0 and result.stdout.strip():
            drv_path = result.stdout.strip()
        else:
            raise NixError(f"Failed to instantiate {self.raw}")

        print(f"Derivation: {drv_path}")
        return drv_path

    def build(self, capture_output: bool = False) -> None:
        """Build using nix-build."""
        if self.attribute:
            build_cmd = ["nix-build", self.file_path, "-A", self.attribute, "--no-out-link"]
        else:
            build_cmd = ["nix-build", self.file_path, "--no-out-link"]
        run_command(build_cmd, capture_output=capture_output)


@dataclass
class AttributeSpec(DerivationSpec):
    """Simple attribute specification (e.g., hello)."""
    attribute: str

    def get_derivation_path(self) -> str:
        """Try flake first, then default.nix."""
        print(f"Instantiating {self.raw}...")

        # First try as flake attribute
        result = run_command(
            ["nix", "path-info", "--derivation", f".#{self.attribute}"],
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            drv_path = result.stdout.strip()
        else:
            # Try with nix-instantiate and default.nix
            result = run_command(
                ["nix-instantiate", ".", "-A", self.attribute],
                check=False
            )

            if result.returncode == 0 and result.stdout.strip():
                drv_path = result.stdout.strip()
            else:
                raise NixError(f"Failed to get derivation path for {self.raw}")

        print(f"Derivation: {drv_path}")
        return drv_path

    def build(self, capture_output: bool = False) -> None:
        """Try flake build first, then nix-build."""
        # Try flake first
        build_cmd = [
            "nix", "build", f".#{self.attribute}", "--no-link",
            "--log-format", "bar-with-logs"
        ]
        result = run_command(build_cmd, check=False, capture_output=capture_output)

        if result.returncode != 0:
            # Fallback to nix-build with default.nix
            build_cmd = ["nix-build", ".", "-A", self.attribute, "--no-out-link"]
            run_command(build_cmd, capture_output=capture_output)


@dataclass
class BenchmarkConfig:
    """Configuration for the benchmark run."""
    derivations: list[DerivationSpec]
    runs: int = 10
    warmup: int = 3
    hyperfine_args: list[str] = field(default_factory=list)


def check_hyperfine() -> None:
    """Check if hyperfine is available in PATH.

    Raises:
        HyperfineError: If hyperfine is not found
    """
    if shutil.which("hyperfine") is None:
        raise HyperfineError(
            "hyperfine not found. Install it with:\n"
            "  nix-env -iA nixpkgs.hyperfine\n"
            "  or nix shell nixpkgs#hyperfine"
        )


def parse_derivation_spec(spec: str) -> DerivationSpec:
    """Parse a derivation specification into the appropriate subclass.

    Args:
        spec: Derivation specification (e.g., "nixpkgs#hello", "-f file.nix -A attr", "hello")

    Returns:
        Appropriate DerivationSpec subclass instance
    """
    # Check for -f file.nix -A attribute syntax
    if "-f" in spec and "-A" in spec:
        parts = spec.split()
        file_idx = parts.index("-f") + 1
        attr_idx = parts.index("-A") + 1

        if file_idx < len(parts) and attr_idx < len(parts):
            return FileSpec(
                raw=spec,
                file_path=parts[file_idx],
                attribute=parts[attr_idx]
            )

    # Check for flake reference (contains #)
    if '#' in spec:
        flake_ref, attr = spec.split('#', 1)
        return FlakeSpec(
            raw=spec,
            flake_ref=flake_ref or ".",
            attribute=attr
        )

    # Check if it's a file path
    if spec.startswith(('.', '/')) or spec.endswith('.nix'):
        return FileSpec(
            raw=spec,
            file_path=spec,
            attribute=None
        )

    # Otherwise it's just an attribute name
    return AttributeSpec(
        raw=spec,
        attribute=spec
    )




def build_dependencies(drv_path: str, batch_size: int = 100) -> None:
    """Build all dependencies of a derivation.

    Args:
        drv_path: Path to the derivation file
        batch_size: Maximum number of derivations to build at once

    Raises:
        NixError: If dependency building fails
    """
    print("Step 2: Building dependencies...")

    # Get all requisites
    result = run_command(
        ["nix-store", "--query", "--requisites", drv_path]
    )

    requisites = [
        req for req in result.stdout.strip().split('\n')
        if req and req != drv_path
    ]

    if requisites:
        print(f"Found {len(requisites)} dependencies to build")

        # Build dependencies in batches to avoid command line limits
        for i in range(0, len(requisites), batch_size):
            batch = requisites[i:i + batch_size]
            print(f"Building batch {i // batch_size + 1}/{(len(requisites) + batch_size - 1) // batch_size} "
                  f"({len(batch)} derivations)...")
            run_command(
                ["nix-store", "--realize", "--quiet"] + batch
            )


def ensure_built(spec: DerivationSpec) -> None:
    """Ensure the derivation is built at least once.

    Args:
        spec: Parsed derivation specification

    Raises:
        NixError: If build fails
    """
    print(f"Ensuring {spec.raw} is built...")

    try:
        spec.build(capture_output=False)
        print(f"Build complete for {spec.raw}")
    except subprocess.CalledProcessError as e:
        raise NixError(f"Build failed for {spec.raw} with exit code {e.returncode}")




def prepare_derivation(spec: DerivationSpec) -> None:
    """Prepare a single derivation for benchmarking.

    Args:
        spec: Parsed derivation specification

    Raises:
        NixError: If preparation fails
    """
    print(f"\n=== Preparing {spec.raw} ===")

    # Get derivation path
    drv_path = spec.get_derivation_path()

    # Build dependencies
    build_dependencies(drv_path)

    # Ensure the package is built
    ensure_built(spec)


def run_benchmark(config: BenchmarkConfig) -> None:
    """Run the benchmark with hyperfine.

    Args:
        config: Benchmark configuration

    Raises:
        NixError: If Nix operations fail
        HyperfineError: If hyperfine is not available or fails
    """
    print(f"=== nix-hyperfine: Benchmarking {len(config.derivations)} derivation(s) ===")

    # Check hyperfine availability
    check_hyperfine()

    # Prepare all derivations first
    print("\nStep 1: Preparing all derivations...")
    for spec in config.derivations:
        prepare_derivation(spec)

    # Build hyperfine commands for all derivations
    build_cmds = []
    for spec in config.derivations:
        build_cmd = f"nix build '{spec.raw}' --rebuild --no-link --log-format bar-with-logs"
        build_cmds.append(build_cmd)

    # Run benchmark
    print(f"\nStep 2: Running benchmark...")
    print(f"Runs: {config.runs} (with {config.warmup} warmup runs)")
    print("Commands:")
    for i, cmd in enumerate(build_cmds, 1):
        print(f"  {i}. {cmd}")
    print()

    # Build hyperfine command with all build commands
    hyperfine_cmd = [
        "hyperfine",
        "--runs", str(config.runs),
        "--warmup", str(config.warmup),
        "--shell", "bash"
    ]

    if config.hyperfine_args:
        hyperfine_cmd.extend(config.hyperfine_args)

    # Add all build commands
    hyperfine_cmd.extend(build_cmds)

    try:
        subprocess.run(hyperfine_cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise HyperfineError(f"Hyperfine failed with exit code {e.returncode}")

    print()
    print("=== Benchmark complete ===")


def parse_args() -> BenchmarkConfig:
    """Parse command line arguments.

    Returns:
        BenchmarkConfig instance
    """
    parser = argparse.ArgumentParser(
        description="Benchmark nix builds with hyperfine, ensuring dependencies are pre-built.",
        epilog=(
            "Examples:\n"
            "  %(prog)s nixpkgs#hello                              # Flake reference\n"
            "  %(prog)s .#package1 .#package2                       # Local flake\n"
            "  %(prog)s '-f release.nix -A hello'                   # Traditional nix file\n"
            "  %(prog)s '-f ./myfile.nix -A pkg1' '-f ./myfile.nix -A pkg2'\n"
            "  %(prog)s hello                                       # Attribute (tries .#hello or ./default.nix -A hello)\n"
            "  %(prog)s nixpkgs#hello nixpkgs#curl                  # Compare multiple\n"
            "  %(prog)s -n 5 -w 1 .#myPackage -- --export-json results.json\n"
            "\n"
            "Supported formats:\n"
            "  - Flake references: nixpkgs#hello, .#attr, /path/to/flake#attr\n"
            "  - Traditional nix: '-f file.nix -A attr' (must be quoted as single argument)\n"
            "  - Simple attributes: hello (tries .#hello, then ./default.nix -A hello)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "derivations",
        nargs="+",
        help="Nix derivations to benchmark (e.g., nixpkgs#hello, .#pkg, or just 'hello')"
    )

    parser.add_argument(
        "-n", "--runs",
        type=int,
        default=10,
        help="Number of benchmark runs (default: 10)"
    )

    parser.add_argument(
        "-w", "--warmup",
        type=int,
        default=3,
        help="Number of warmup runs (default: 3)"
    )

    # Capture remaining arguments for hyperfine
    parser.add_argument(
        "hyperfine_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to hyperfine (use -- before them)"
    )

    args = parser.parse_args()

    # Remove '--' from hyperfine args if present
    hyperfine_args = args.hyperfine_args
    if hyperfine_args and hyperfine_args[0] == '--':
        hyperfine_args = hyperfine_args[1:]

    # Parse all derivation specs upfront
    parsed_derivations = [parse_derivation_spec(d) for d in args.derivations]

    return BenchmarkConfig(
        derivations=parsed_derivations,
        runs=args.runs,
        warmup=args.warmup,
        hyperfine_args=hyperfine_args
    )


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        config = parse_args()
        run_benchmark(config)
        return 0
    except (NixError, HyperfineError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
