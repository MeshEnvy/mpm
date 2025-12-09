"""Version command for mpm."""

import tomllib
from pathlib import Path


def get_mpm_version():
    """Get the version of mesh-plugin-manager from pyproject.toml or installed package."""
    # First, try to read from pyproject.toml (development mode)
    # Find pyproject.toml relative to this package
    # Package is at vendor/mpm/src/mesh_plugin_manager/
    # pyproject.toml is at vendor/mpm/pyproject.toml
    package_dir = Path(__file__).parent.parent.parent.parent
    pyproject_path = package_dir / "pyproject.toml"

    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                version = data.get("project", {}).get("version")
                if version:
                    return version
        except Exception:
            pass

    # Fallback: try to get from installed package metadata
    try:
        from importlib.metadata import version as get_package_version
        return get_package_version("mesh-plugin-manager")
    except Exception:
        return "unknown"


def cmd_version(args):
    """Display the version of mesh-plugin-manager."""
    print(get_mpm_version())
