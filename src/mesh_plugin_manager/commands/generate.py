"""Generate command for mpm."""

import sys

from mesh_plugin_manager.build_utils import find_project_dir, scan_plugins
from mesh_plugin_manager.modules import generate_dynamic_modules
from mesh_plugin_manager.proto import generate_all_protobuf_files


def register(subparsers):
    """Register the generate command."""
    parser = subparsers.add_parser("generate", help="Generate protobuf files for all plugins")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    return cmd_generate


def cmd_generate(args):
    """Generate protobuf files and dynamic modules for all plugins."""
    project_dir = find_project_dir()
    plugins = scan_plugins(project_dir)

    if not plugins:
        print("No plugins found.")
        # Still generate empty DynamicModules.cpp
        generate_dynamic_modules(project_dir, [], verbose=args.verbose)
        return

    print(f"Generating protobuf files for {len(plugins)} plugin(s)...")
    success_count, total_count = generate_all_protobuf_files(plugins, verbose=args.verbose)

    print(f"\nCompleted - {success_count}/{total_count} protobuf file(s) generated successfully")

    if success_count < total_count:
        sys.exit(1)

    # Generate dynamic modules after protobuf generation
    print("\nGenerating dynamic modules...")
    if not generate_dynamic_modules(project_dir, plugins, verbose=args.verbose):
        print("Warning: Failed to generate dynamic modules", file=sys.stderr)
