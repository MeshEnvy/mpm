"""Firmware patching functionality for mpm."""

import os
import subprocess
import sys
from pathlib import Path
from importlib import resources


def _get_patch_path():
    """Get the path to the firmware patch file."""
    try:
        # Try using importlib.resources (Python 3.9+)
        with resources.path("mesh_plugin_manager.patches", "firmware-patch.diff") as patch_path:
            return str(patch_path)
    except (AttributeError, ModuleNotFoundError):
        # Fallback for older Python or if package not installed
        # Try relative path from this module
        module_dir = Path(__file__).parent
        patch_path = module_dir / "patches" / "firmware-patch.diff"
        if patch_path.exists():
            return str(patch_path)
        raise FileNotFoundError("Could not find firmware-patch.diff")


def apply_patch(project_dir):
    """
    Apply the firmware patch to enable plugin support.

    Args:
        project_dir: Root directory of the firmware project

    Returns:
        True if patch was applied successfully, False otherwise
    """
    project_path = Path(project_dir)
    patch_path = _get_patch_path()

    # Check if this is a git repository
    if not (project_path / ".git").exists():
        print("Error: Project directory is not a git repository", file=sys.stderr)
        return False

    # Apply the patch (idempotent - git apply handles already-applied patches)
    try:
        result = subprocess.run(
            ["git", "apply", patch_path],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Successfully applied firmware patch.")
            return True
        else:
            # Check if patch is already applied (common case for idempotency)
            if "already applied" in result.stderr.lower() or "patch does not apply" in result.stderr.lower():
                # Try reverse check to confirm it's already applied
                result_reverse = subprocess.run(
                    ["git", "apply", "--reverse", "--check", patch_path],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                )
                if result_reverse.returncode == 0:
                    print("Patch is already applied.")
                    return True
            print(f"Error applying patch: {result.stderr}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("Error: git command not found", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False



