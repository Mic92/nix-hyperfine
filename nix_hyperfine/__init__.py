"""nix-hyperfine: Benchmark Nix builds with hyperfine."""

import sys

from .benchmark import BenchmarkMode, benchmark_build, benchmark_eval
from .colors import error
from .dependencies import check_hyperfine
from .exceptions import HyperfineError, NixError
from .parser import parse_args


def main() -> None:
    """Execute main program entry point."""
    try:
        # Check hyperfine is available
        check_hyperfine()

        # Parse arguments
        args = parse_args()

        # Run appropriate benchmark
        match args.mode:
            case BenchmarkMode.EVAL:
                benchmark_eval(args.specs, args.hyperfine_args)
            case BenchmarkMode.BUILD:
                benchmark_build(args.specs, args.hyperfine_args)

    except (NixError, HyperfineError) as e:
        print(error(f"Error: {e}"), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(error("\nInterrupted"), file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        print(error(f"Unexpected error: {e}"), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
