"""Derivation specification classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .command import run_command


@dataclass
class DerivationSpec(ABC):
    """Base class for parsed derivation specifications."""

    raw: str  # Original specification string

    @abstractmethod
    def get_derivation_path(self) -> str:
        """Get the derivation path (.drv file)."""

    @abstractmethod
    def build(self, capture_output: bool = False) -> None:
        """Build the derivation."""


@dataclass
class FlakeSpec(DerivationSpec):
    """Flake reference specification (e.g., nixpkgs#hello)."""

    flake_ref: str
    attribute: str

    def get_derivation_path(self) -> str:
        """Get the derivation path (.drv file) using nix path-info."""
        cmd = ["nix", "path-info", "--derivation", f"{self.flake_ref}#{self.attribute}"]
        result = run_command(cmd)
        return result.stdout.strip()

    def build(self, capture_output: bool = False) -> None:
        """Build using nix build with flake reference."""
        cmd = ["nix", "build", f"{self.flake_ref}#{self.attribute}"]
        run_command(cmd, capture_output=capture_output)


@dataclass
class FileSpec(DerivationSpec):
    """Traditional nix file specification (e.g., -f file.nix -A attr)."""

    file_path: str
    attribute: str | None = None

    def get_derivation_path(self) -> str:
        """Get the derivation path (.drv file) using nix-instantiate."""
        cmd = ["nix-instantiate", self.file_path]
        if self.attribute:
            cmd.extend(["-A", self.attribute])
        result = run_command(cmd)
        return result.stdout.strip()

    def build(self, capture_output: bool = False) -> None:
        """Build using nix-build with file and optional attribute."""
        cmd = ["nix-build", self.file_path]
        if self.attribute:
            cmd.extend(["-A", self.attribute])
        run_command(cmd, capture_output=capture_output)


@dataclass
class AttributeSpec(DerivationSpec):
    """Simple attribute specification (e.g., hello)."""

    attribute: str

    def get_derivation_path(self) -> str:
        """Get the derivation path (.drv file) using nix-instantiate."""
        cmd = ["nix-instantiate", "-A", self.attribute]
        result = run_command(cmd)
        return result.stdout.strip()

    def build(self, capture_output: bool = False) -> None:
        """Build using nix-build with attribute."""
        cmd = ["nix-build", "-A", self.attribute]
        run_command(cmd, capture_output=capture_output)
