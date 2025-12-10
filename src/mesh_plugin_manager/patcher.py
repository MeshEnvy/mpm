"""Firmware patching functionality for mpm."""

import os
import re
import subprocess
import sys
from pathlib import Path
from importlib import resources


def _parse_version(version_str):
    """Parse version string (e.g., '2.6.13' or 'v2.7.16') into tuple for comparison."""
    # Remove 'v' prefix if present
    version_str = version_str.lstrip('v')
    parts = version_str.split('.')
    # Pad to 3 parts (major.minor.patch)
    while len(parts) < 3:
        parts.append('0')
    try:
        return tuple(int(p) for p in parts[:3])
    except ValueError:
        return (0, 0, 0)


def _get_current_branch_or_tag(project_path):
    """Get the current branch name or tag name from git."""
    try:
        # First, check if we're on a branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            # If not detached HEAD, return branch name
            if branch != "HEAD":
                return branch
        
        # Check if we're on a tag
        result = subprocess.run(
            ["git", "describe", "--exact-match", "--tags", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_firmware_version(project_path):
    """
    Get the firmware version from git tags or version.properties.
    Returns version string or None.
    """
    try:
        # Get the nearest tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            # Extract version from tag (e.g., "v2.7.16" -> "2.7.16")
            version_match = re.search(r'v?(\d+\.\d+\.\d+)', tag)
            if version_match:
                return version_match.group(1)
        
        # Fallback: try to get version from version.properties
        version_props = project_path / "version.properties"
        if version_props.exists():
            with open(version_props, 'r') as f:
                content = f.read()
                # Look for major.minor.build pattern
                match = re.search(r'major\s*=\s*(\d+).*minor\s*=\s*(\d+).*build\s*=\s*(\d+)', content, re.DOTALL)
                if match:
                    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    except Exception:
        pass
    return None


def _find_available_patches():
    """Find all available patch files."""
    patches = []
    # Use filesystem approach - patches are in the same package directory
    module_dir = Path(__file__).parent
    patches_dir = module_dir / "patches"
    if patches_dir.exists():
        for patch_file in patches_dir.glob("firmware-patch-v*.diff"):
            patches.append(str(patch_file))
    
    return patches


def _find_named_patch(tag_name):
    """Find a patch file for a non-version tag (e.g., firmware-patch-develop.diff)."""
    module_dir = Path(__file__).parent
    patches_dir = module_dir / "patches"
    if patches_dir.exists():
        patch_path = patches_dir / f"firmware-patch-{tag_name}.diff"
        if patch_path.exists():
            return str(patch_path)
    return None


def _get_patch_path(project_dir):
    """
    Get the path to the appropriate firmware patch file.
    Priority:
    1. Exact match for current branch/tag name (e.g., firmware-patch-develop.diff)
    2. Version-based matching (latest patch <= firmware version)
    3. Fallback to firmware-patch.diff
    4. Panic with error
    """
    project_path = Path(project_dir)
    module_dir = Path(__file__).parent
    patches_dir = module_dir / "patches"
    
    # Step 1: Check for exact branch/tag match first
    branch_or_tag = _get_current_branch_or_tag(project_path)
    if branch_or_tag:
        # Strip 'v' prefix if present (e.g., "vdevelop" -> "develop")
        clean_name = branch_or_tag.lstrip('v')
        named_patch = _find_named_patch(clean_name)
        if named_patch:
            print(f"Found exact match patch file for '{branch_or_tag}': {Path(named_patch).name}")
            return named_patch
    
    # Step 2: Fall back to version-based matching
    firmware_version = _get_firmware_version(project_path)
    if firmware_version:
        firmware_ver_tuple = _parse_version(firmware_version)
        
        # Find all available versioned patches
        available_patches = _find_available_patches()
        if available_patches:
            # Extract versions from patch filenames and filter compatible ones
            compatible_patches = []
            for patch_path in available_patches:
                # Extract version from filename (e.g., "firmware-patch-v2.6.13.diff" -> "2.6.13")
                match = re.search(r'firmware-patch-v(\d+\.\d+\.\d+)\.diff', Path(patch_path).name)
                if match:
                    patch_version = match.group(1)
                    patch_ver_tuple = _parse_version(patch_version)
                    # Only include patches where patch version <= firmware version
                    if patch_ver_tuple <= firmware_ver_tuple:
                        compatible_patches.append((patch_ver_tuple, patch_path))
            
            if compatible_patches:
                # Sort by version (descending) and return the latest compatible patch
                compatible_patches.sort(key=lambda x: x[0], reverse=True)
                selected_patch = compatible_patches[0][1]
                selected_version = ".".join(str(v) for v in compatible_patches[0][0])
                print(f"Selected patch version {selected_version} for firmware version {firmware_version}")
                return selected_patch
    
    # Step 3: Fallback to old naming convention
    patch_path = patches_dir / "firmware-patch.diff"
    if patch_path.exists():
        print("Using fallback patch file: firmware-patch.diff")
        return str(patch_path)
    
    # Step 4: Panic - no patch found
    available_patches = []
    if patches_dir.exists():
        available_patches = [p.name for p in patches_dir.glob("firmware-patch-*.diff")]
    
    error_msg = "Could not find any compatible firmware patch file.\n"
    if branch_or_tag:
        error_msg += f"Current branch/tag: '{branch_or_tag}'\n"
        error_msg += f"Expected patch file: 'firmware-patch-{branch_or_tag.lstrip('v')}.diff'\n"
    if firmware_version:
        error_msg += f"Firmware version: {firmware_version}\n"
    error_msg += f"Available patches: {available_patches}"
    
    raise FileNotFoundError(error_msg)


def _has_conflict_markers(file_path):
    """Check if a file contains git conflict markers."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            # Check for definitive git conflict markers
            return "<<<<<<<" in content or ">>>>>>>" in content
    except Exception:
        return False


def apply_patch(project_dir):
    """
    Apply the firmware patch to enable plugin support.
    Uses 3-way merge to create conflict markers when patches don't apply cleanly.

    Args:
        project_dir: Root directory of the firmware project

    Returns:
        True if patch was applied successfully or conflicts were created, False otherwise
    """
    project_path = Path(project_dir)
    patch_path = _get_patch_path(project_dir)

    # Check if this is a git repository
    if not (project_path / ".git").exists():
        print("Error: Project directory is not a git repository", file=sys.stderr)
        return False

    # Apply the patch using 3-way merge to create conflicts when needed
    try:
        result = subprocess.run(
            ["git", "apply", "--3way", patch_path],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Successfully applied firmware patch.")
            return True
        else:
            # Check if patch is already applied (common case for idempotency)
            if "already applied" in result.stderr.lower():
                print("Patch is already applied.")
                return True

            # Check if conflicts were created (this is what we want)
            # Scan for conflict markers in files mentioned in the patch
            conflicts_found = False
            conflicted_files = []
            patch_content = Path(patch_path).read_text(encoding="utf-8", errors="ignore")
            for line in patch_content.split("\n"):
                if line.startswith("diff --git"):
                    # Extract filename from "diff --git a/path b/path"
                    parts = line.split()
                    if len(parts) >= 4:
                        file_path = project_path / parts[2].lstrip("a/")
                        if file_path.exists() and _has_conflict_markers(file_path):
                            conflicts_found = True
                            conflicted_files.append(str(file_path.relative_to(project_path)))

            if conflicts_found:
                print("Patch conflicts detected. Files contain conflict markers. Please resolve conflicts manually.")
                print(f"Conflicted files: {', '.join(conflicted_files)}")
                if result.stderr:
                    print(f"Patch output: {result.stderr}", file=sys.stderr)
                return True

            # If no conflicts but patch failed, it's a real error
            print(f"Error applying patch: {result.stderr}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("Error: git command not found", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False



