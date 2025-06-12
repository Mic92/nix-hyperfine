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

  # Run tests with pytest
  checkPhase = ''
    runHook preCheck

    # Set up test environment
    export HOME=$TMPDIR
    export NIX_PATH=nixpkgs=${nixpkgs}

    # Run pytest
    pytest tests -v

    runHook postCheck
  '';
})
