"""Watch command for mpm."""

import os
import time
from pathlib import Path

from mesh_plugin_manager.build_utils import find_project_dir, scan_plugins
from mesh_plugin_manager.proto import generate_all_protobuf_files


def cmd_watch(args):
    """Watch for changes and regenerate protobuf files."""
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
