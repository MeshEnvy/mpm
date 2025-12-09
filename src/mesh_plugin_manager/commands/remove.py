"""Remove command for mpm."""

import sys

from mesh_plugin_manager.build_utils import find_project_dir
from mesh_plugin_manager.installer import PluginInstaller
from mesh_plugin_manager.manifest import ManifestManager


def register(subparsers):
    """Register the remove command."""
    parser = subparsers.add_parser("remove", help="Remove a plugin")
    parser.add_argument("plugin", help="Plugin slug to remove")
    return cmd_remove


def cmd_remove(args):
    """Remove a plugin."""
    project_dir = find_project_dir()
    manifest = ManifestManager(project_dir)
    installer = PluginInstaller(project_dir)
    lockfile = manifest.read_lockfile()

    plugin_slug = args.plugin

    # Check if plugin is installed
    if not installer.is_plugin_installed(plugin_slug):
        print(f"Plugin {plugin_slug} is not installed.")
        return

    # Check if other plugins depend on this one
    dependents = []
    if "plugins" in lockfile:
        for slug, plugin_data in lockfile["plugins"].items():
            if slug == plugin_slug:
                continue
            deps = plugin_data.get("dependencies", {})
            if plugin_slug in deps:
                dependents.append(slug)

    if dependents:
        print(f"Error: Cannot remove {plugin_slug}. The following plugins depend on it:")
        for dep in dependents:
            print(f"  - {dep}")
        sys.exit(1)

    # Remove plugin
    if installer.remove_plugin(plugin_slug):
        # Remove from manifest if it's a direct dependency
        manifest.remove_dependency(plugin_slug)

        # Remove from lockfile
        manifest.remove_lockfile_plugin(plugin_slug)

        print(f"Removed {plugin_slug}")
    else:
        print(f"Error removing {plugin_slug}", file=sys.stderr)
        sys.exit(1)
