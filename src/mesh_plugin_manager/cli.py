"""Command-line interface for mpm."""

import argparse
import sys

from mesh_plugin_manager.commands.bump import cmd_bump
from mesh_plugin_manager.commands.generate import cmd_generate
from mesh_plugin_manager.commands.init import cmd_init
from mesh_plugin_manager.commands.install import cmd_install
from mesh_plugin_manager.commands.list import cmd_list
from mesh_plugin_manager.commands.remove import cmd_remove
from mesh_plugin_manager.commands.version import cmd_version, get_mpm_version
from mesh_plugin_manager.commands.watch import cmd_watch


def main():
    """Main entry point for CLI."""
    version = get_mpm_version()
    parser = argparse.ArgumentParser(
        description=f"Mesh Plugin Manager (v{version})",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # list command
    list_parser = subparsers.add_parser("list", help="List plugins")
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="List all available plugins from registry",
    )

    # install command
    install_parser = subparsers.add_parser("install", help="Install plugins")
    install_parser.add_argument(
        "plugins",
        nargs="*",
        help="Plugin slugs to install (if not specified, installs all from meshtastic.json)",
    )

    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a plugin")
    remove_parser.add_argument("plugin", help="Plugin slug to remove")

    # generate command
    generate_parser = subparsers.add_parser("generate", help="Generate protobuf files for all plugins")
    generate_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )

    # watch command
    watch_parser = subparsers.add_parser("watch", help="Watch for changes and regenerate protobuf files")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize firmware for plugin support")

    # bump command
    bump_parser = subparsers.add_parser("bump", help="Bump plugin version in plugin.h")
    bump_parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Version bump type (major, minor, or patch)",
    )

    # version command
    version_parser = subparsers.add_parser("version", help="Display version information")

    args = parser.parse_args()

    if not args.command:
        # Default: show help
        parser.print_help()
        sys.exit(0)

    # Route to appropriate command handler
    if args.command == "list":
        cmd_list(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "bump":
        cmd_bump(args)
    elif args.command == "version":
        cmd_version(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

