{
  nix-hyperfine,
  nixpkgs,
}:

nix-hyperfine.overridePythonAttrs (old: {
  # Enable tests for the check
  doCheck = true;

  # Additional test dependencies if needed
  # All dependencies are already provided by the base package
  nativeCheckInputs = old.nativeCheckInputs or [ ];

  # Set up test environment before checks
  preCheck = ''
    export HOME=$TMPDIR
    export NIX_PATH=nixpkgs=${nixpkgs}
  '';

  # Use pytestCheckPhase which handles the test execution
  # Additional flags can be specified here if needed
  # Base configuration is in pyproject.toml
  pytestFlagsArray = [
    "-s" # No capture, show print output
  ];
})
