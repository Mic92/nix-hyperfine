{
  nix-hyperfine,
}:

nix-hyperfine.overridePythonAttrs (_old: {
  # Enable tests for the check
  doCheck = true;
})
