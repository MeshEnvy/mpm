"""Command-line interface for mpm."""

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

from mesh_plugin_manager.commands.version import get_mpm_version


def _discover_commands():
    """Discover all command modules and return a dict mapping command name to handler."""
    commands = {}
    commands_module = Path(__file__).parent / "commands"
    
    # Import all modules in the commands package
    for _, module_name, _ in pkgutil.iter_modules([str(commands_module)]):
        if module_name == "__init__":
            continue
        
        try:
            module = importlib.import_module(f"mesh_plugin_manager.commands.{module_name}")
            if hasattr(module, "register"):
                # Store the module for later registration
                commands[module_name] = module
        except ImportError:
            continue
    
    return commands


def main():
    """Main entry point for CLI."""
    version = get_mpm_version()
    parser = argparse.ArgumentParser(
        description=f"Mesh Plugin Manager (v{version})",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Discover and register all commands
    command_handlers = {}
    command_modules = _discover_commands()
    
    for module_name, module in command_modules.items():
        handler = module.register(subparsers)
        # Map command name (from parser) to handler
        # The command name is typically the same as module name
        command_name = module_name
        command_handlers[command_name] = handler

    args = parser.parse_args()

    if not args.command:
        # Default: show help
        parser.print_help()
        sys.exit(0)

    # Route to appropriate command handler
    if args.command in command_handlers:
        command_handlers[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

