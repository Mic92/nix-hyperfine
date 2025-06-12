{
  description = "Benchmarks Nix build and evaluation times using hyperfine";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ ./formatter.nix ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      perSystem =
        {
          config,
          pkgs,
          ...
        }:
        let
          # Import package definitions using callPackage
          nix-hyperfine = pkgs.callPackage ./packages/nix-hyperfine.nix { };
        in
        {
          packages = {
            default = nix-hyperfine;
            inherit nix-hyperfine;
          };

          devShells = {
            default = pkgs.callPackage ./devShells/default.nix {
              treefmt = config.treefmt.build.wrapper;
            };
          };

          checks = {
            tests = pkgs.callPackage ./checks/tests.nix {
              inherit nix-hyperfine;
              nixpkgs = inputs.nixpkgs;
            };
          };
        };
    };
}
