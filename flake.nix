{
  description = "Wrapper around hyperfine for benchmarking Nix builds";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];

      perSystem = { config, self', inputs', pkgs, system, ... }: 
        let
          python = pkgs.python312;
          
          nix-hyperfine = pkgs.writeScriptBin "nix-hyperfine" ''
            #!${python}/bin/python3
            ${builtins.readFile ./nix_hyperfine.py}
          '';

          pythonEnv = python.withPackages (ps: with ps; [
            pytest
            pytest-cov
            mypy
          ]);
        in
        {
          packages = {
            default = nix-hyperfine;
            nix-hyperfine = nix-hyperfine;
          };

          apps = {
            default = {
              type = "app";
              program = "${nix-hyperfine}/bin/nix-hyperfine";
            };
            nix-hyperfine = {
              type = "app";
              program = "${nix-hyperfine}/bin/nix-hyperfine";
            };
          };

          devShells = {
            default = pkgs.mkShell {
              buildInputs = with pkgs; [
                pythonEnv
                hyperfine
                nix
                ruff
              ];

              shellHook = ''
                echo "nix-hyperfine development shell"
                echo "Run 'pytest' to run tests"
                echo "Run 'mypy nix_hyperfine.py' to type check"
                echo "Run 'ruff check' to lint"
                echo "Run 'ruff format' to format code"
              '';
            };
          };

          checks = {
            tests = pkgs.runCommand "nix-hyperfine-tests" {
              buildInputs = [ pythonEnv nix-hyperfine pkgs.nix pkgs.hyperfine ];
            } ''
              # Copy test files
              cp -r ${./tests} tests
              cp ${./nix_hyperfine.py} nix_hyperfine.py
              
              # Make nix-hyperfine available in PATH
              export PATH="${nix-hyperfine}/bin:$PATH"
              
              # Run pytest
              ${pythonEnv}/bin/pytest tests -v
              
              touch $out
            '';

            formatting = pkgs.runCommand "nix-hyperfine-format-check" {
              buildInputs = [ pkgs.ruff ];
            } ''
              cp ${./nix_hyperfine.py} nix_hyperfine.py
              cp -r ${./tests} tests
              ${pkgs.ruff}/bin/ruff format --check .
              touch $out
            '';

            linting = pkgs.runCommand "nix-hyperfine-lint-check" {
              buildInputs = [ pkgs.ruff ];
            } ''
              cp ${./nix_hyperfine.py} nix_hyperfine.py
              cp -r ${./tests} tests
              ${pkgs.ruff}/bin/ruff check .
              touch $out
            '';

            typing = pkgs.runCommand "nix-hyperfine-type-check" {
              buildInputs = [ pythonEnv ];
            } ''
              cp ${./nix_hyperfine.py} nix_hyperfine.py
              ${pythonEnv}/bin/mypy nix_hyperfine.py
              touch $out
            '';
          };
        };
    };
}