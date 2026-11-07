"""Base class defining the standard lifecycle for all ecosystem addons."""

import abc
from pathlib import Path
from typing import Optional


class BaseAddon(abc.ABC):
    """Abstract base class for all big-data ecosystem addons."""

    id: str
    name: str
    description: str
    default_version: str
    default_ports: dict[str, int]
    install_dir: Path

    @abc.abstractmethod
    def is_installed(self) -> bool:
        """Check if addon is installed on the filesystem."""
        pass

    @abc.abstractmethod
    def get_installed_version(self) -> Optional[str]:
        """Return the version string of the installed addon, or None."""
        pass

    @abc.abstractmethod
    def is_running(self) -> bool:
        """Check if addon services/daemons are actively running."""
        pass

    @abc.abstractmethod
    def install(self, version: Optional[str] = None) -> bool:
        """Download, extract, and configure the addon."""
        pass

    @abc.abstractmethod
    def start(self) -> bool:
        """Start addon services/daemons."""
        pass

    @abc.abstractmethod
    def stop(self) -> bool:
        """Stop addon services/daemons."""
        pass

    @abc.abstractmethod
    def status(self) -> dict:
        """Return a structured dictionary with status details."""
        pass

    @abc.abstractmethod
    def remove(self) -> bool:
        """Stop, remove installation directory, and clean environment variables."""
        pass
