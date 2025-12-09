"""Init command for mpm."""

import sys

from mesh_plugin_manager.build_utils import find_project_dir
from mesh_plugin_manager.patcher import apply_patch


def register(subparsers):
    """Register the init command."""
    parser = subparsers.add_parser("init", help="Initialize firmware for plugin support")
    return cmd_init


def cmd_init(args):
    """Initialize firmware for plugin support by applying the patch."""
    project_dir = find_project_dir()

    if not apply_patch(project_dir):
        sys.exit(1)
