"""Build utility functions shared between build.py and other modules."""

import os


def find_project_dir(start_dir=None):
    """
    Find the project directory (where platformio.ini is located).

    Args:
        start_dir: Starting directory for search (defaults to current working directory)

    Returns:
        str: Path to project directory
    """
    if start_dir is None:
        start_dir = os.getcwd()

    current_dir = os.path.abspath(start_dir)

    # Start from the current directory and walk up
    search_dir = current_dir
    while search_dir != os.path.dirname(search_dir):  # Stop at filesystem root
        platformio_ini = os.path.join(search_dir, "platformio.ini")
        if os.path.exists(platformio_ini):
            return search_dir
        search_dir = os.path.dirname(search_dir)

    # Fallback: return current directory
    return current_dir


def scan_plugins(project_dir):
    """
    Scan for plugins in the project directory.

    Args:
        project_dir: Root directory of the project

    Returns:
        List of tuples (plugin_name, plugin_path, src_path, proto_files)
    """
    plugins_dir_rel = "plugins"
    plugins_dir = os.path.join(project_dir, plugins_dir_rel)

    if not os.path.exists(plugins_dir):
        return []

    plugins = []
    if not os.path.isdir(plugins_dir):
        return plugins

    plugin_dirs = [
        d
        for d in os.listdir(plugins_dir)
        if os.path.isdir(os.path.join(plugins_dir, d)) and not d.startswith(".")
    ]

    for plugin_name in plugin_dirs:
        plugin_path = os.path.join(plugins_dir, plugin_name)
        src_path = os.path.join(plugin_path, "src")

        # Check if plugin has a src directory
        if not os.path.isdir(src_path):
            continue

        # Scan for .proto files recursively in the plugin directory
        proto_files = []
        for root, dirs, files in os.walk(plugin_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.endswith(".proto"):
                    proto_files.append(os.path.join(root, file))

        plugins.append((plugin_name, plugin_path, src_path, proto_files))

    return plugins

