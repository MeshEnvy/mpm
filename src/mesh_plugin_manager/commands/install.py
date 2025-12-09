"""Install command for mpm."""

import sys

from mesh_plugin_manager.build_utils import find_project_dir
from mesh_plugin_manager.installer import PluginInstaller
from mesh_plugin_manager.manifest import ManifestManager
from mesh_plugin_manager.registry import RegistryClient
from mesh_plugin_manager.resolver import DependencyResolver


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
