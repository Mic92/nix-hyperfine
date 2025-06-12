{
  mkShell,
  python3,
  hyperfine,
  nix,
  deadnix,
  treefmt,
}:

mkShell {
  buildInputs = [
    (python3.withPackages (
      ps: with ps; [
        pytest
        mypy
      ]
    ))
    hyperfine
    nix
    deadnix
    treefmt
  ];

  shellHook = ''
    echo "nix-hyperfine development shell"
    echo "Run 'pytest' to run tests"
    echo "Run 'treefmt' to format and check code"
  '';
}
