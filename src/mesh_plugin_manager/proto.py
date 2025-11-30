"""Protobuf generation functions."""

import os
import subprocess
import sys


def generate_protobuf_files(proto_file, options_file=None, output_dir=None, nanopb_dir=None):
    """
    Generate protobuf C++ files using nanopb.

    Args:
        proto_file: Path to the .proto file
        options_file: Optional path to .options file
        output_dir: Optional output directory (defaults to proto file directory)
        nanopb_dir: Optional nanopb directory (unused, kept for compatibility)

    Returns:
        bool: True if successful, False otherwise
    """
    # Resolve proto file path
    proto_file = os.path.abspath(proto_file)
    if not os.path.exists(proto_file):
        print(f"Error: Proto file not found: {proto_file}")
        return False

    # Get proto directory and filename
    proto_dir = os.path.dirname(proto_file)
    proto_basename = os.path.basename(proto_file)
    proto_name = os.path.splitext(proto_basename)[0]

    # Determine output directory
    if output_dir is None:
        output_dir = proto_dir
    else:
        output_dir = os.path.abspath(output_dir)

    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)

    # Auto-detect options file if not specified
    if options_file is None:
        candidate_options = os.path.join(proto_dir, f"{proto_name}.options")
        if os.path.exists(candidate_options):
            options_file = candidate_options
            print(f"Auto-detected options file: {options_file}")
    elif options_file:
        options_file = os.path.abspath(options_file)
        if not os.path.exists(options_file):
            print(f"Warning: Options file not found: {options_file}")
            options_file = None

    # Always generate protobuf files
    print(f"Generating protobuf files from {proto_basename}...")

    # Note: nanopb_generator should be in the PATH, otherwise this will fail.
    # Tyically, pip handles this by adding the virtualenv/bin directory to the PATH.
    # If you have made pip install to an alternate directory, you may need to add the directory to the PATH.
    # For example, if you have made pip install to a directory called "myenv", you may need to add the directory to the PATH.
    # export PATH=$PATH:/path/to/myenv/bin
    cmd = [
        "nanopb_generator",
        "-D",
        output_dir,
        "-I",
        proto_dir,
        "-S",
        ".cpp",
        proto_file,
    ]

    try:
        # Run in proto directory so nanopb can find the .options file
        # We use cwd argument instead of os.chdir to avoid thread-safety issues in SCons
        result = subprocess.run(cmd, cwd=proto_dir, check=True, capture_output=True, text=True)
        # if result.stdout:
        #     print(result.stdout)
        # if result.stderr:
        #     print(result.stderr)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error generating protobufs: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def generate_all_protobuf_files(plugins, verbose=True):
    """
    Generate protobuf files for all proto files found in plugins.

    Args:
        plugins: List of plugin tuples from scan_plugins()
        verbose: Whether to print status messages

    Returns:
        Tuple of (success_count, total_count)
    """
    success_count = 0
    total_count = 0

    for plugin_name, plugin_path, src_path, proto_files in plugins:
        for proto_file in proto_files:
            total_count += 1
            proto_basename = os.path.basename(proto_file)
            proto_dir = os.path.dirname(proto_file)
            proto_name = os.path.splitext(proto_basename)[0]

            # Check for options file
            options_file = os.path.join(proto_dir, f"{proto_name}.options")
            options_path = options_file if os.path.exists(options_file) else None

            if verbose:
                print(f"MPM: Processing {proto_basename} from {plugin_name}...")

            if generate_protobuf_files(proto_file, options_path, proto_dir, None):
                success_count += 1
            elif verbose:
                print(f"MPM: Failed to generate protobuf files for {proto_basename}")

    return success_count, total_count

