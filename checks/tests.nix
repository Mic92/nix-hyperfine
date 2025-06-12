{
  nix-hyperfine,
  python3,
  nix,
  hyperfine,
  git,
  nixpkgs,
}:

nix-hyperfine.overridePythonAttrs (old: {
  # Enable tests for the check
  doCheck = true;

  # Additional test dependencies if needed
  nativeCheckInputs = old.nativeCheckInputs or [ ] ++ [
    nix
    hyperfine
    python3.pkgs.pytestCheckHook
    git
  ];

  # Set up test environment before checks
  preCheck = ''
    export HOME=$TMPDIR
    export NIX_PATH=nixpkgs=${nixpkgs}
  '';

  # Use pytestCheckPhase which handles the test execution
  pytestFlagsArray = [
    "-v"
    "--no-capture-output"
  ];
})
