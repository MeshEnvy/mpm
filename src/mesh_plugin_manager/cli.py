"""Command-line interface for mpm."""

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path

import semver

from mesh_plugin_manager.build_utils import find_project_dir, scan_plugins
from mesh_plugin_manager.installer import PluginInstaller
from mesh_plugin_manager.manifest import ManifestManager
from mesh_plugin_manager.modules import generate_dynamic_modules
from mesh_plugin_manager.patcher import apply_patch
from mesh_plugin_manager.proto import generate_all_protobuf_files
from mesh_plugin_manager.registry import RegistryClient
from mesh_plugin_manager.resolver import DependencyResolver


def get_mpm_version():
    """Get the version of mesh-plugin-manager from pyproject.toml or installed package."""
    # First, try to read from pyproject.toml (development mode)
    # Find pyproject.toml relative to this package
    # Package is at vendor/mpm/src/mesh_plugin_manager/
    # pyproject.toml is at vendor/mpm/pyproject.toml
    package_dir = Path(__file__).parent.parent.parent
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


def cmd_install(args):
    """Install plugins."""
    project_dir = find_project_dir()
    manifest = ManifestManager(project_dir)
    registry_client = RegistryClient()
    installer = PluginInstaller(project_dir)

    # Fetch registry
    print("Fetching registry...")
    try:
        registry = registry_client.fetch_registry(force_refresh=True)
    except Exception as e:
        print(f"Error fetching registry: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine which plugins to install
    if args.plugins:
        # Install specified plugins
        plugins_to_install = {}
        for plugin_spec in args.plugins:
            # Parse spec (could be "slug" or "slug@version")
            if "@" in plugin_spec:
                slug, version_spec = plugin_spec.split("@", 1)
            else:
                slug = plugin_spec
                version_spec = "latest"

            plugins_to_install[slug] = version_spec
    else:
        # Install all from manifest
        manifest_data = manifest.read_manifest()
        plugins_to_install = manifest_data.get("plugins", {})

    if not plugins_to_install:
        print("No plugins to install.")
        return

    # Resolve dependencies
    print("Resolving dependencies...")
    resolver = DependencyResolver(registry, project_dir)

    # Convert version specs to requirements
    requirements = {}
    for slug, spec in plugins_to_install.items():
        if spec == "latest":
            # Get latest version from registry
            if slug in registry:
                plugin_info = registry[slug]
                if "version" in plugin_info:
                    spec = plugin_info["version"]
                else:
                    print(f"Error: No version information found for {slug}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"Error: Plugin {slug} not found in registry", file=sys.stderr)
                sys.exit(1)
        requirements[slug] = spec

    try:
        resolutions = resolver.resolve(requirements)
    except Exception as e:
        print(f"Error resolving dependencies: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nResolved {len(resolutions)} plugin(s):")
    for slug, version in resolutions.items():
        print(f"  {slug}@{version}")

    # Install plugins
    print("\nInstalling plugins...")
    for slug, version in resolutions.items():
        if slug not in registry:
            print(f"Error: Plugin {slug} not found in registry", file=sys.stderr)
            continue

        plugin_info = registry[slug]
        repo_url = plugin_info.get("repo")
        if not repo_url:
            print(f"Error: No repository URL for {slug}", file=sys.stderr)
            continue

        tag = f"v{version}"

        print(f"Installing {slug}@{version}...")
        if installer.install_plugin(slug, repo_url, version, tag):
            # Get commit SHA
            commit_sha = installer.get_plugin_commit(slug)
            if not commit_sha:
                commit_sha = tag

            # Get dependencies from plugin manifest
            plugin_manifest = manifest.get_plugin_manifest(slug)
            dependencies = {}
            if plugin_manifest:
                dependencies = plugin_manifest.get("dependencies", {})

            # Update lockfile
            is_transitive = slug not in plugins_to_install
            manifest.update_lockfile_plugin(slug, version, repo_url, commit_sha, dependencies, is_transitive)

            # Add to root manifest if it's a direct dependency
            if slug in plugins_to_install:
                version_spec = plugins_to_install[slug]
                if version_spec != version:
                    version_spec = f"^{version}"  # Use caret for compatible versions
                manifest.add_dependency(slug, version_spec)

            print(f"  ✓ Installed {slug}@{version}")
        else:
            print(f"  ✗ Failed to install {slug}", file=sys.stderr)

    print("\nInstallation complete!")


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


def cmd_watch(args):
    """Watch for changes and regenerate protobuf files."""
    import time
    from pathlib import Path
    from mesh_plugin_manager.proto import generate_all_protobuf_files
    
    project_dir = find_project_dir()
    plugins_dir = Path(project_dir) / "plugins"
    
    if not plugins_dir.exists():
        print("No plugins directory found.")
        return
    
    print("Watching for changes in plugins... (Press Ctrl+C to stop)")
    
    # Track last modification times
    last_mtimes = {}
    
    def get_all_proto_files():
        """Get all .proto files in plugins directory."""
        proto_files = []
        for root, dirs, files in os.walk(plugins_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.endswith(".proto"):
                    proto_files.append(Path(root) / file)
        return proto_files
    
    def check_for_changes():
        """Check if any proto files have changed."""
        proto_files = get_all_proto_files()
        changed = False
        
        for proto_file in proto_files:
            try:
                mtime = proto_file.stat().st_mtime
                if proto_file not in last_mtimes or mtime > last_mtimes[proto_file]:
                    last_mtimes[proto_file] = mtime
                    changed = True
            except OSError:
                pass
        
        return changed
    
    # Initial generation
    plugins = scan_plugins(project_dir)
    if plugins:
        print(f"Initial generation for {len(plugins)} plugin(s)...")
        generate_all_protobuf_files(plugins, verbose=True)
    
    # Watch loop
    try:
        while True:
            time.sleep(1)  # Check every second
            if check_for_changes():
                print("\nChanges detected, regenerating protobuf files...")
                plugins = scan_plugins(project_dir)
                if plugins:
                    generate_all_protobuf_files(plugins, verbose=True)
                    print("Regeneration complete.\n")
    except KeyboardInterrupt:
        print("\nStopped watching.")


def cmd_init(args):
    """Initialize firmware for plugin support by applying the patch."""
    project_dir = find_project_dir()

    if not apply_patch(project_dir):
        sys.exit(1)


def cmd_bump(args):
    """Bump plugin version in meta.h file."""
    bump_type = args.bump_type.lower()
    
    if bump_type not in ("major", "minor", "patch"):
        print(f"Error: Invalid bump type '{bump_type}'. Must be one of: major, minor, patch", file=sys.stderr)
        sys.exit(1)
    
    # Get current working directory
    cwd = Path.cwd()
    
    # Look for meta.h in current directory or src/meta.h
    meta_h_paths = [
        cwd / "meta.h",
        cwd / "src" / "meta.h",
    ]
    
    meta_h_path = None
    for path in meta_h_paths:
        if path.exists():
            meta_h_path = path
            break
    
    if not meta_h_path:
        print("Error: meta.h not found. Expected meta.h or src/meta.h in the current directory.", file=sys.stderr)
        sys.exit(1)
    
    # Read meta.h
    try:
        with open(meta_h_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {meta_h_path}: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get plugin name from directory name
    plugin_name = cwd.name.upper()
    version_pattern = rf'#define\s+{plugin_name}_VERSION\s+"(\d+\.\d+\.\d+)"'
    
    # Find version string
    match = re.search(version_pattern, content)
    if not match:
        print(f"Error: Could not find {plugin_name}_VERSION in {meta_h_path}", file=sys.stderr)
        print(f"Expected: #define {plugin_name}_VERSION \"X.Y.Z\"", file=sys.stderr)
        sys.exit(1)
    
    current_version_str = match.group(1)
    
    # Parse and bump version
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError as e:
        print(f"Error: Invalid version format '{current_version_str}': {e}", file=sys.stderr)
        sys.exit(1)
    
    # Apply bump
    if bump_type == "major":
        new_version = current_version.bump_major()
    elif bump_type == "minor":
        new_version = current_version.bump_minor()
    else:  # patch
        new_version = current_version.bump_patch()
    
    new_version_str = str(new_version)
    
    # Replace version in content
    new_content = content.replace(current_version_str, new_version_str)
    
    # Write updated content
    try:
        with open(meta_h_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        print(f"Error writing {meta_h_path}: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Bumping version: {current_version_str} → {new_version_str} ({bump_type})")
    print(f"✓ Updated {meta_h_path.relative_to(cwd)}")
    
    # Search up directory tree for registry/registry.json
    plugin_slug = cwd.name.lower()
    registry_path = None
    search_dir = cwd.parent
    
    # Search up to 10 levels (reasonable limit)
    for _ in range(10):
        potential_registry = search_dir / "registry" / "registry.json"
        if potential_registry.exists():
            registry_path = potential_registry
            break
        if search_dir == search_dir.parent:  # Reached root
            break
        search_dir = search_dir.parent
    
    if registry_path:
        try:
            # Read registry.json
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            # Update version if plugin entry exists
            if plugin_slug in registry_data:
                registry_data[plugin_slug]["version"] = new_version_str
                
                # Write back with proper formatting (2 space indent)
                with open(registry_path, 'w', encoding='utf-8') as f:
                    json.dump(registry_data, f, indent=2, ensure_ascii=False)
                    # Add trailing newline for consistency
                    f.write('\n')
                
                # Show relative path from workspace root if possible
                try:
                    # Try to find workspace root (where registry/ is)
                    workspace_root = registry_path.parent.parent
                    rel_path = registry_path.relative_to(workspace_root)
                    print(f"✓ Updated {rel_path}")
                except (ValueError, AttributeError):
                    # Fallback to showing just the filename
                    print(f"✓ Updated registry/registry.json")
            else:
                print(f"  Note: Plugin '{plugin_slug}' not found in registry.json")
        except Exception as e:
            print(f"  Warning: Could not update registry.json: {e}", file=sys.stderr)
    
    print(f"New version: {new_version_str}")


def cmd_version(args):
    """Display the version of mesh-plugin-manager."""
    print(get_mpm_version())


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
    bump_parser = subparsers.add_parser("bump", help="Bump plugin version in meta.h")
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

