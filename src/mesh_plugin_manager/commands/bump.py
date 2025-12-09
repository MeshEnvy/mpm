"""Bump command for mpm."""

import json
import re
import sys
from pathlib import Path

import semver

from mesh_plugin_manager.build_utils import find_project_dir


def register(subparsers):
    """Register the bump command."""
    parser = subparsers.add_parser("bump", help="Bump plugin version in plugin.h")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Version bump type (major, minor, or patch)",
    )
    return cmd_bump


def cmd_bump(args):
    """Bump plugin version in plugin.h file."""
    bump_type = args.bump_type.lower()

    if bump_type not in ("major", "minor", "patch"):
        print(f"Error: Invalid bump type '{bump_type}'. Must be one of: major, minor, patch", file=sys.stderr)
        sys.exit(1)

    # Get current working directory
    cwd = Path.cwd()

    # Look for plugin.h in current directory or src/plugin.h
    plugin_h_paths = [
        cwd / "plugin.h",
        cwd / "src" / "plugin.h",
    ]

    plugin_h_path = None
    for path in plugin_h_paths:
        if path.exists():
            plugin_h_path = path
            break

    if not plugin_h_path:
        print("Error: plugin.h not found. Expected plugin.h or src/plugin.h in the current directory.", file=sys.stderr)
        sys.exit(1)

    # Read plugin.h
    try:
        with open(plugin_h_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {plugin_h_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Get plugin name from directory name
    plugin_name = cwd.name.upper()
    version_pattern = rf'#define\s+{plugin_name}_VERSION\s+"(\d+\.\d+\.\d+)"'

    # Find version string
    match = re.search(version_pattern, content)
    if not match:
        print(f"Error: Could not find {plugin_name}_VERSION in {plugin_h_path}", file=sys.stderr)
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
        with open(plugin_h_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        print(f"Error writing {plugin_h_path}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Bumping version: {current_version_str} → {new_version_str} ({bump_type})")
    print(f"✓ Updated {plugin_h_path.relative_to(cwd)}")

    # Search up directory tree for registry.json
    plugin_slug = cwd.name.lower()
    registry_path = None
    search_dir = cwd.parent

    # Search up to 10 levels (reasonable limit)
    for _ in range(10):
        potential_registry = search_dir / "public" / "registry.json"
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
                    print(f"✓ Updated registry.json")
            else:
                print(f"  Note: Plugin '{plugin_slug}' not found in registry.json")
        except Exception as e:
            print(f"  Warning: Could not update registry.json: {e}", file=sys.stderr)

    print(f"New version: {new_version_str}")
