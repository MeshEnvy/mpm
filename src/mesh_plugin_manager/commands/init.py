"""Init command for mpm."""

import sys
from pathlib import Path

from mesh_plugin_manager.build_utils import find_project_dir
from mesh_plugin_manager.patcher import apply_patch


def register(subparsers):
    """Register the init command."""
    parser = subparsers.add_parser("init", help="Initialize firmware for plugin support")
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Target directory (defaults to current directory)",
    )
    return cmd_init


def cmd_init(args):
    """Initialize firmware for plugin support by applying the patch."""
    if args.target:
        project_dir = Path(args.target).resolve()
        if not project_dir.exists():
            print(f"Error: Target directory '{args.target}' does not exist", file=sys.stderr)
            sys.exit(1)
        if not project_dir.is_dir():
            print(f"Error: Target '{args.target}' is not a directory", file=sys.stderr)
            sys.exit(1)
        # Verify it's a valid project directory (has platformio.ini)
        platformio_ini = project_dir / "platformio.ini"
        if not platformio_ini.exists():
            print(f"Error: Target directory '{args.target}' does not contain platformio.ini", file=sys.stderr)
            sys.exit(1)
    else:
        project_dir = find_project_dir()

    if not apply_patch(project_dir):
        sys.exit(1)
