# nix-hyperfine

A wrapper around [hyperfine](https://github.com/sharkdp/hyperfine) for benchmarking Nix builds with proper dependency handling.

## Features

- **Dependency Pre-building**: Automatically builds all dependencies before benchmarking to ensure accurate measurements
- **Multiple Format Support**: Works with flakes, traditional Nix files, and simple attributes
- **Intelligent Parsing**: Automatically detects the format of your derivation specification
- **Modern Python**: Written in Python 3.12+ with full type annotations

## Installation

### Using Nix Flakes

```bash
# Run directly
nix run github:yourusername/nix-hyperfine -- nixpkgs#hello

# Install to profile
nix profile install github:yourusername/nix-hyperfine

# Or add to your flake inputs
{
  inputs.nix-hyperfine.url = "github:yourusername/nix-hyperfine";
  # ...
}
```

### Traditional Nix

```bash
nix-env -if https://github.com/yourusername/nix-hyperfine/archive/main.tar.gz
```

## Usage

```bash
# Benchmark a flake package
nix-hyperfine nixpkgs#hello

# Benchmark multiple packages
nix-hyperfine nixpkgs#hello nixpkgs#curl

# Benchmark local flake packages
nix-hyperfine .#package1 .#package2

# Benchmark traditional Nix expressions
nix-hyperfine '-f release.nix -A hello'

# Benchmark with custom runs and warmup
nix-hyperfine -n 5 -w 1 nixpkgs#hello

# Pass additional arguments to hyperfine
nix-hyperfine nixpkgs#hello -- --export-json results.json
```

### Supported Formats

1. **Flake references**: `nixpkgs#hello`, `.#attr`, `/path/to/flake#attr`
2. **Traditional Nix**: `'-f file.nix -A attr'` (must be quoted as single argument)
3. **Simple attributes**: `hello` (tries `.#hello`, then `./default.nix -A hello`)

## How It Works

1. **Instantiation**: Converts the derivation specification to a `.drv` file
2. **Dependency Building**: Builds all dependencies using `nix-store --realize`
3. **Pre-build**: Ensures the package is built at least once
4. **Benchmarking**: Runs hyperfine with `nix build --rebuild` to measure build time

## Development

```bash
# Run tests
nix develop -c pytest

# Run with coverage
nix develop -c pytest --cov=nix_hyperfine

# Format code
nix develop -c black .
nix develop -c isort .

# Type check
nix develop -c mypy nix_hyperfine.py
```

## Requirements

- Python 3.12+
- Nix with flakes support (optional, for flake references)
- hyperfine

## License

MIT