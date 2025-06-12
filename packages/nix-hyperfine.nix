{
  lib,
  python3,
  hyperfine,
  makeWrapper,
  nix,
  git,
  fileset ? lib.fileset,
}:

let
  python = python3;

  # Define source files using fileset
  sourceFiles = fileset.toSource {
    root = ./..;
    fileset = fileset.unions [
      ../nix_hyperfine
      ../tests
      ../pyproject.toml
    ];
  };
in
python.pkgs.buildPythonApplication {
  pname = "nix-hyperfine";
  version = "0.1.0";
  pyproject = true;

  src = sourceFiles;

  build-system = with python.pkgs; [
    setuptools
  ];

  dependencies = [ ];

  # Use pytestCheckPhase which handles the test execution
  # Additional flags can be specified here if needed
  # Base configuration is in pyproject.toml
  pytestFlagsArray = [
    "-s" # No capture, show print output
  ];

  nativeCheckInputs =
    with python.pkgs;
    [
      pytestCheckHook
      pytest-xdist
    ]
    ++ [
      nix
      hyperfine
      git
    ];

  # Tests are run separately in checks/tests.nix
  doCheck = false;

  # Wrap the executable to include hyperfine in PATH
  postInstall = ''
    wrapProgram $out/bin/nix-hyperfine \
      --prefix PATH : ${lib.makeBinPath [ hyperfine ]}
  '';

  nativeBuildInputs = [ makeWrapper ];

  meta = with lib; {
    description = "Benchmarks Nix build and evaluation times using hyperfine";
    homepage = "https://github.com/Mic92/nix-hyperfine";
    license = licenses.mit;
    maintainers = [ ];
    mainProgram = "nix-hyperfine";
  };
}
