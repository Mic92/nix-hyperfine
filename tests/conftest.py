"""Pytest configuration for nix-hyperfine tests."""

import sys
from pathlib import Path

# Add the parent directory to Python path so we can import nix_hyperfine
sys.path.insert(0, str(Path(__file__).parent.parent))