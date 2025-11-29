"""PlatformIO build integration functions."""

import os

try:
    Import("env")  # noqa: F821 - SCons/PlatformIO provides Import and env
    IS_PLATFORMIO = True
except:
    IS_PLATFORMIO = False

from mpm.build_utils import find_project_dir, scan_plugins
from mpm.proto import generate_all_protobuf_files


def init_plugins(env, projenv=None):
    """
    Scan for plugins, update build filters, and handle protobuf generation.

    Args:
        env: Build environment (for SRC_FILTER and protobuf actions)
        projenv: Project environment (for CPPPATH - include paths)
    """
    project_dir = env["PROJECT_DIR"]
    plugins_dir_rel = "plugins"

    # Use projenv if provided, otherwise fall back to env
    include_env = projenv if projenv is not None else env

    # env.Append(SRC_FILTER=[f"-<{plugins_dir_rel}/*>"])

    print(f"MPM: Scanning plugins in {plugins_dir_rel}...")

    plugins = scan_plugins(project_dir)

    if not plugins:
        print(f"MPM: No plugins directory found at {plugins_dir_rel}")
        return

    for plugin_name, plugin_path, src_path, proto_files in plugins:
        print(f"MPM: Found plugin {plugin_name}")

        # Update SRC_FILTER
        rel_src_path = os.path.relpath(src_path, project_dir)
        env.Append(SRC_FILTER=[f"+<../{rel_src_path}/*>"])

        # Add plugin src to include paths (use projenv for compiler include paths)
        include_env.Append(CPPPATH=[src_path])
        print(f"MPM: Added include path {rel_src_path}")

        # Log proto files for this plugin
        for proto_file in proto_files:
            proto_basename = os.path.basename(proto_file)
            print(f"MPM: Registered proto {proto_basename} for {plugin_name}")

    # print("MPM: SRC_FILTER: ", env["SRC_FILTER"])

    # Generate protobuf files for all plugins
    generate_all_protobuf_files(plugins, verbose=True)


# PlatformIO integration happens via bin/mpm.py, not here

