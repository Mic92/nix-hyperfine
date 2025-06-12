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

    # Set up git for tests
    git config --global user.name "Test User"
    git config --global user.email "test@example.com"
    git config --global init.defaultBranch main

    # Ensure nix can access experimental features for flakes
    mkdir -p $HOME/.config/nix
    echo "experimental-features = nix-command flakes" > $HOME/.config/nix/nix.conf

    # Run pytest
    pytest tests -v

    runHook postCheck
  '';
})
