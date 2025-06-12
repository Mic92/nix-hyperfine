"""nix-hyperfine: Benchmark Nix builds with hyperfine."""

import sys

from .benchmark import BenchmarkMode, benchmark_build, benchmark_eval
from .dependencies import check_hyperfine
from .exceptions import HyperfineError, NixError
from .parser import parse_args

__version__ = "0.1.0"


def main() -> None:
    """Main entry point."""
    try:
        # Check hyperfine is available
        check_hyperfine()

        # Parse arguments
        specs, mode, hyperfine_args = parse_args()

        # Run appropriate benchmark
        if mode == BenchmarkMode.EVAL:
            benchmark_eval(specs, hyperfine_args)
        else:
            benchmark_build(specs, hyperfine_args)

    except (NixError, HyperfineError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
