#!/usr/bin/env bash
# Demo script showing various nix-hyperfine usage patterns

set -euo pipefail

echo "=== nix-hyperfine Demo ==="
echo

# Create a simple test flake
cat > flake.nix << 'EOF'
{
  outputs = { self, nixpkgs }: {
    packages.x86_64-linux = let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
    in {
      fast = pkgs.runCommand "fast-build" {} "echo fast > $out";
      slow = pkgs.runCommand "slow-build" {} "sleep 1 && echo slow > $out";
    };
  };
}
EOF

echo "1. Benchmarking flake packages:"
echo "   nix-hyperfine .#fast .#slow"
echo

echo "2. Benchmarking nixpkgs packages:"
echo "   nix-hyperfine nixpkgs#hello nixpkgs#cowsay"
echo

echo "3. Benchmarking with custom parameters:"
echo "   nix-hyperfine -n 3 -w 1 nixpkgs#hello -- --export-json results.json"
echo

echo "Try running these commands!"