# nix-hyperfine

A command-line tool that uses [hyperfine](https://github.com/sharkdp/hyperfine) to benchmark Nix derivation builds and evaluations.

## What it does

nix-hyperfine provides accurate benchmarks for Nix builds by:
- Pre-building all dependencies to ensure they don't affect timing measurements
- Forcing rebuilds to get consistent results
- Supporting both build performance and evaluation performance measurements
- Comparing performance across git history

## Features

- **Multiple benchmark modes**: Measure build time (default) or evaluation time (`--eval`)
- **Flexible input formats**: Support for flakes (`nixpkgs#hello`), traditional Nix files (`-f file.nix`), and simple attributes
- **Git revision comparison**: Benchmark the same derivation across different git commits using `@` syntax
- **Dependency isolation**: Automatically builds all dependencies before benchmarking
- **User-friendly output**: Shows benchmark names that match your input
- **Hyperfine integration**: Pass any hyperfine arguments after `--` for full control

## Installation

### Using Nix

```bash
# Run directly without installation
nix run github:Mic92/nix-hyperfine -- hello

# Show help
nix run github:Mic92/nix-hyperfine -- --help
```

### From source

```bash
git clone https://github.com/Mic92/nix-hyperfine
cd nix-hyperfine
nix develop
python -m nix_hyperfine --help
```

## Usage

### Basic usage

Benchmark building a derivation:
```bash
nix run github:Mic92/nix-hyperfine -- hello
```

Benchmark building multiple derivations:
```bash
nix run github:Mic92/nix-hyperfine -- hello cowsay lolcat
```

### Demo

See nix-hyperfine in action benchmarking NixOS tests:

[![asciicast](https://asciinema.org/a/Fe3GqUrDTS0fEgw3fs9L2chPn.svg)](https://asciinema.org/a/Fe3GqUrDTS0fEgw3fs9L2chPn)

*Demo shows benchmarking `nixosTests.ferm` across git revisions*

### Benchmark modes

By default, nix-hyperfine benchmarks the build phase. You can also benchmark evaluation:

```bash
# Benchmark evaluation time
nix run github:Mic92/nix-hyperfine -- --eval hello

# Benchmark build time (default)
nix run github:Mic92/nix-hyperfine -- --build hello
```

### Different input formats

```bash
# Flake references
nix run github:Mic92/nix-hyperfine -- nixpkgs#hello nixpkgs#cowsay

# Traditional nix files
nix run github:Mic92/nix-hyperfine -- "-f default.nix -A hello"

# Simple attributes (from current directory)
nix run github:Mic92/nix-hyperfine -- hello
```

### Benchmarking across git revisions

You can benchmark the same derivation across different git revisions using the `@` syntax:

```bash
# Compare current version with previous commit
nix run github:Mic92/nix-hyperfine -- hello@HEAD,HEAD~1

# Compare multiple revisions
nix run github:Mic92/nix-hyperfine -- hello@main,staging,v23.11

# Works with any spec format
nix run github:Mic92/nix-hyperfine -- "nixpkgs#hello@main,v23.11"
nix run github:Mic92/nix-hyperfine -- "-f default.nix -A myapp@HEAD~1,HEAD"

# Multiple revisions separated by commas
nix run github:Mic92/nix-hyperfine -- hello@HEAD~3,HEAD~2,HEAD~1,HEAD
```

This feature uses `builtins.fetchGit` to fetch each revision into the Nix store before benchmarking, allowing you to compare performance across your git history.

### Passing arguments to hyperfine

Any arguments after `--` are passed directly to hyperfine:

```bash
nix run github:Mic92/nix-hyperfine -- hello -- --runs 10 --warmup 3
```

## Help

```
usage: nix-hyperfine [-h] [--build | --eval] derivations [derivations ...]

Benchmark Nix derivation builds with hyperfine

positional arguments:
  derivations  Derivation specifications (e.g., "nixpkgs#hello", "-f file.nix
               -A attr", "hello", "hello@HEAD~1,main")

options:
  -h, --help   show this help message and exit
  --build      Benchmark building derivations (default)
  --eval       Benchmark evaluating derivations

Any additional arguments after -- are passed directly to hyperfine
```

## How it works

### Build Mode (default)

When benchmarking builds with `nix run github:Mic92/nix-hyperfine -- hello` or `nix run github:Mic92/nix-hyperfine -- --build hello`:

1. First, nix-hyperfine instantiates the derivation to get the `.drv` file
2. It builds all dependencies (build-time dependencies)
3. It pre-builds the package once to ensure all runtime dependencies are available
4. Finally, it runs hyperfine with the appropriate nix build command (using `--rebuild` to force rebuilds)

### Eval Mode

When benchmarking evaluation with `nix run github:Mic92/nix-hyperfine -- --eval hello`:

1. First, nix-hyperfine instantiates the derivation to get the `.drv` file
2. It builds all dependencies (build-time dependencies) to ensure they don't affect timing
3. Finally, it runs hyperfine with the appropriate nix instantiation command

In both modes, nix-hyperfine ensures that hyperfine only measures the actual build/eval time, not dependency fetching or building. The key difference is that eval mode measures how long it takes Nix to evaluate the expression and produce a derivation, while build mode measures how long it takes to actually build that derivation.

## Example Output

### Basic Build Benchmark

```bash
$ nix run github:Mic92/nix-hyperfine -- nixpkgs#cowsay
Pre-building nixpkgs#cowsay...
  Pre-build completed in 0.81s
Running: hyperfine -n nixpkgs#cowsay nix --extra-experimental-features 'nix-command flakes' build nixpkgs#cowsay --rebuild
Benchmark 1: nixpkgs#cowsay
  Time (mean ± σ):     549.5 ms ± 181.3 ms    [User: 17.2 ms, System: 11.4 ms]
  Range (min … max):   442.3 ms … 758.8 ms    10 runs
 
  Warning: The first benchmarking run for this command was significantly slower than the rest (758.8 ms). This could be caused by (filesystem) caches that were not filled until after the first run. You should consider using the '--warmup' option to fill those caches before the actual benchmark. Alternatively, use the '--prepare' option to clear the caches before each timing run.
```

### Comparing Multiple Packages

```bash
$ nix run github:Mic92/nix-hyperfine -- hello cowsay -- --runs 5 --warmup 2
Pre-building hello...
  Pre-build completed in 0.45s
Pre-building cowsay...
  Pre-build completed in 0.63s
Running: hyperfine --runs 5 --warmup 2 -n hello -n cowsay nix --extra-experimental-features 'nix-command flakes' build nixpkgs#hello --rebuild nix --extra-experimental-features 'nix-command flakes' build nixpkgs#cowsay --rebuild
Benchmark 1: hello
  Time (mean ± σ):     334.2 ms ±  15.7 ms    [User: 12.1 ms, System: 8.3 ms]
  Range (min … max):   318.5 ms … 356.8 ms    5 runs
 
Benchmark 2: cowsay
  Time (mean ± σ):     421.8 ms ±  22.4 ms    [User: 15.7 ms, System: 10.2 ms]
  Range (min … max):   395.2 ms … 448.1 ms    5 runs
 
Summary
  hello ran
    1.26 ± 0.09 times faster than cowsay
```

### Evaluation Benchmarks

```bash
$ nix run github:Mic92/nix-hyperfine -- --eval nixpkgs#hello -- --runs 5
Running: hyperfine --runs 5 -n nixpkgs#hello nix --extra-experimental-features 'nix-command flakes' eval nixpkgs#hello --raw
Benchmark 1: nixpkgs#hello
  Time (mean ± σ):     517.7 ms ±  38.4 ms    [User: 285.2 ms, System: 101.4 ms]
  Range (min … max):   451.1 ms … 563.0 ms    5 runs
```

### Git Revision Comparison

```bash
$ nix run github:Mic92/nix-hyperfine -- "nixpkgs#hello@main,staging" -- --runs 3
Pre-building nixpkgs#hello@main...
  Pre-build completed in 0.52s
Pre-building nixpkgs#hello@staging...
  Pre-build completed in 0.49s
Running: hyperfine --runs 3 -n nixpkgs#hello@main -n nixpkgs#hello@staging [commands...]
Benchmark 1: nixpkgs#hello@main
  Time (mean ± σ):     345.1 ms ±  12.3 ms    [User: 13.2 ms, System: 9.1 ms]
  Range (min … max):   334.2 ms … 358.7 ms    3 runs
 
Benchmark 2: nixpkgs#hello@staging
  Time (mean ± σ):     352.4 ms ±  18.7 ms    [User: 14.1 ms, System: 9.8 ms]
  Range (min … max):   338.9 ms … 374.2 ms    3 runs
 
Summary
  nixpkgs#hello@main ran
    1.02 ± 0.07 times faster than nixpkgs#hello@staging
```

## License

MIT
