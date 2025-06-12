{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  perSystem = {
    treefmt = {
      # Used to find the project root
      projectRootFile = "flake.lock";

      programs.deadnix.enable = true;
      programs.mypy.enable = true;
      programs.nixfmt.enable = true;
      programs.ruff.format = true;
      programs.ruff.check = true;
    };
  };
}
