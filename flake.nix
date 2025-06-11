{
  description = "Wrapper around hyperfine for benchmarking Nix builds";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];

      perSystem = { config, self', inputs', pkgs, system, lib, ... }: 
        let
          python = pkgs.python312;
          
          # Define source files using fileset
          sourceFiles = lib.fileset.toSource {
            root = ./.;
            fileset = lib.fileset.unions [
              ./nix_hyperfine.py
              ./tests
              ./pyproject.toml
            ];
          };
          
          nix-hyperfine = pkgs.stdenv.mkDerivation {
            pname = "nix-hyperfine";
            version = "0.1.0";
            
            src = lib.fileset.toSource {
              root = ./.;
              fileset = ./nix_hyperfine.py;
            };
            
            buildInputs = [ python ];
            
            dontBuild = true;
            
            installPhase = ''
              mkdir -p $out/bin
              cp $src/nix_hyperfine.py $out/bin/nix-hyperfine
              chmod +x $out/bin/nix-hyperfine
              substituteInPlace $out/bin/nix-hyperfine \
                --replace "#!/usr/bin/env python3" "#!${python}/bin/python3"
            '';
            
            meta = with lib; {
              description = "Wrapper around hyperfine for benchmarking Nix builds";
              homepage = "https://github.com/yourusername/nix-hyperfine";
              license = licenses.mit;
              maintainers = [ ];
              mainProgram = "nix-hyperfine";
              platforms = platforms.all;
            };
          };

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
            tests = pkgs.stdenv.mkDerivation {
              name = "nix-hyperfine-tests";
              src = sourceFiles;
              buildInputs = [ pythonEnv nix-hyperfine pkgs.nix pkgs.hyperfine pkgs.which ];
              buildPhase = ''
                # Make nix-hyperfine available in PATH
                export PATH="${nix-hyperfine}/bin:$PATH"
                
                # Run pytest
                pytest tests -v
              '';
              installPhase = ''
                touch $out
              '';
            };

            formatting = pkgs.stdenv.mkDerivation {
              name = "nix-hyperfine-format-check";
              src = sourceFiles;
              buildInputs = [ pkgs.ruff ];
              buildPhase = ''
                ruff format --check .
              '';
              installPhase = ''
                touch $out
              '';
            };

            linting = pkgs.stdenv.mkDerivation {
              name = "nix-hyperfine-lint-check";
              src = sourceFiles;
              buildInputs = [ pkgs.ruff ];
              buildPhase = ''
                ruff check .
              '';
              installPhase = ''
                touch $out
              '';
            };

            typing = pkgs.stdenv.mkDerivation {
              name = "nix-hyperfine-type-check";
              src = sourceFiles;
              buildInputs = [ pythonEnv ];
              buildPhase = ''
                mypy nix_hyperfine.py
              '';
              installPhase = ''
                touch $out
              '';
            };
          };
        };
    };
}