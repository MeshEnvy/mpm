"""New command for mpm."""

import json
import os
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, PackageLoader


def register(subparsers):
    """Register the new command."""
    parser = subparsers.add_parser("new", help="Create a new plugin")
    parser.add_argument("name", help="Plugin name (slug)")
    parser.add_argument(
        "destination",
        nargs="?",
        default=None,
        help="Destination directory (defaults to current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing plugin directory if it exists",
    )
    return cmd_new


def cmd_new(args):
    """Create a new plugin."""
    plugin_slug = args.name.lower()
    plugin_name = _slug_to_name(plugin_slug)
    plugin_name_upper = plugin_name.upper()
    
    cwd = Path.cwd()
    
    # Determine destination directory
    if args.destination:
        dest_dir = Path(args.destination).resolve()
        if dest_dir.exists():
            if not dest_dir.is_dir():
                print(f"Error: Destination '{args.destination}' exists but is not a directory", file=sys.stderr)
                sys.exit(1)
        else:
            # Create the destination directory if it doesn't exist
            print(f"Creating destination directory '{args.destination}'...")
            dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        dest_dir = cwd
    
    plugin_dir = dest_dir / plugin_slug
    
    # Check if directory already exists
    if plugin_dir.exists():
        if args.force:
            print(f"Removing existing directory '{plugin_slug}'...")
            shutil.rmtree(plugin_dir)
        else:
            print(f"Error: Directory '{plugin_slug}' already exists. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)
    
    # Validate plugin slug
    if not re.match(r'^[a-z0-9-]+$', plugin_slug):
        print(f"Error: Plugin slug must contain only lowercase letters, numbers, and hyphens", file=sys.stderr)
        sys.exit(1)
    
    # Create directory structure
    plugin_dir.mkdir()
    src_dir = plugin_dir / "src"
    src_dir.mkdir()
    
    # Load Jinja2 templates
    env = Environment(loader=PackageLoader("mesh_plugin_manager", "templates"))
    plugin_slug_cpp = _slug_to_cpp_identifier(plugin_slug)
    plugin_slug_snake_upper = _slug_to_snake_case_upper(plugin_slug)
    template_context = {
        "plugin_slug": plugin_slug,
        "plugin_slug_cpp": plugin_slug_cpp,
        "plugin_slug_snake_upper": plugin_slug_snake_upper,
        "plugin_name": plugin_name,
        "plugin_name_upper": plugin_name_upper,
    }
    
    # Create plugin.h
    plugin_h_template = env.get_template("plugin.h.j2")
    (src_dir / "plugin.h").write_text(plugin_h_template.render(**template_context))
    
    # Create module header file
    module_h_template = env.get_template("Module.h.j2")
    (src_dir / f"{plugin_name}Module.h").write_text(module_h_template.render(**template_context))
    
    # Create module implementation file
    module_cpp_template = env.get_template("Module.cpp.j2")
    (src_dir / f"{plugin_name}Module.cpp").write_text(module_cpp_template.render(**template_context))
    
    # Create README.md
    readme_template = env.get_template("README.md.j2")
    (plugin_dir / "README.md").write_text(readme_template.render(**template_context))
    
    # Create .gitignore
    gitignore_template = env.get_template(".gitignore.j2")
    (plugin_dir / ".gitignore").write_text(gitignore_template.render(**template_context))
    
    # Show relative path from cwd for user feedback
    try:
        rel_path = plugin_dir.relative_to(cwd)
        print(f"Created plugin '{plugin_slug}' in {rel_path}")
    except ValueError:
        # If plugin_dir is not relative to cwd, show absolute path
        print(f"Created plugin '{plugin_slug}' in {plugin_dir}")
    
    # Search up for registry.json
    registry_path = _find_registry_json(cwd)
    if registry_path:
        try:
            # Read registry.json
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            # Add plugin entry
            registry_data[plugin_slug] = {
                "name": plugin_name,
                "description": f"A Meshtastic firmware plugin",
                "version": "0.0.1",
                "dependencies": {
                    "meshtastic": ">=2.7.0"
                }
            }
            
            # Write back
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            
            # Show relative path
            try:
                workspace_root = registry_path.parent.parent
                rel_path = registry_path.relative_to(workspace_root)
                print(f"✓ Added to {rel_path}")
            except (ValueError, AttributeError):
                print(f"✓ Added to registry.json")
        except Exception as e:
            print(f"  Warning: Could not update registry.json: {e}", file=sys.stderr)
    else:
        print(f"  Note: registry.json not found (searched up from {cwd})")


def _slug_to_name(slug):
    """Convert a slug to a readable name."""
    # Split by hyphens and capitalize each word
    parts = slug.split('-')
    return ''.join(word.capitalize() for word in parts)


def _slug_to_cpp_identifier(slug):
    """Convert a slug to a valid C++ identifier (camelCase)."""
    # Split by hyphens
    parts = slug.split('-')
    if not parts:
        return slug
    # First part stays lowercase, rest get capitalized
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])


def _slug_to_snake_case_upper(slug):
    """Convert a slug to UPPER_SNAKE_CASE."""
    # Replace hyphens with underscores and convert to uppercase
    return slug.replace('-', '_').upper()


def _find_registry_json(start_dir):
    """Search up directory tree for mesh-forge/public/registry.json."""
    search_dir = Path(start_dir).resolve()
    
    # Search up to 10 levels (reasonable limit)
    for _ in range(10):
        potential_registry = search_dir / "public" / "registry.json"
        if potential_registry.exists():
            return potential_registry
        
        # Check if we've reached the root
        parent = search_dir.parent
        if parent == search_dir:  # Reached filesystem root
            break
        search_dir = parent
    
    return None

