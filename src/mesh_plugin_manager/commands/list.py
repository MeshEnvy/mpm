"""List command for mpm."""

import sys

from mesh_plugin_manager.build_utils import find_project_dir, scan_plugins
from mesh_plugin_manager.manifest import ManifestManager
from mesh_plugin_manager.registry import RegistryClient


def cmd_list(args):
    """List installed or available plugins."""
    project_dir = find_project_dir()
    manifest = ManifestManager(project_dir)
    lockfile = manifest.read_lockfile()

    if args.all:
        # List all plugins from registry
        print("Fetching registry...")
        registry_client = RegistryClient()
        try:
            registry = registry_client.fetch_registry(force_refresh=True)
            print(f"\nAvailable plugins ({len(registry)}):")
            for slug, info in sorted(registry.items()):
                name = info.get("name", slug)
                version = info.get("version", "unknown")
                print(f"  {slug:20} {name:30} v{version}")
        except Exception as e:
            print(f"Error fetching registry: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # List installed plugins
        plugins = scan_plugins(project_dir)
        if not plugins:
            print("No plugins installed.")
            return

        print(f"Installed plugins ({len(plugins)}):")
        for plugin_name, plugin_path, src_path, proto_files in plugins:
            version = "unknown"
            if "plugins" in lockfile and plugin_name in lockfile["plugins"]:
                version = lockfile["plugins"][plugin_name].get("version", "unknown")
            print(f"  {plugin_name:20} v{version}")
