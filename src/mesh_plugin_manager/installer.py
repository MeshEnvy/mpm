"""Plugin installer for cloning and managing plugin repositories."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class PluginInstaller:
    """Handles installation and removal of plugins."""

    def __init__(self, project_dir: str):
        """
        Initialize installer.

        Args:
            project_dir: Root project directory
        """
        self.project_dir = Path(project_dir)
        self.plugins_dir = self.project_dir / "plugins"

    def install_plugin(
        self,
        plugin_slug: str,
        repo_url: str,
        version: str,
        tag: Optional[str] = None,
    ) -> bool:
        """
        Install a plugin by cloning its repository.

        Args:
            plugin_slug: Slug of the plugin
            repo_url: Git repository URL
            version: Version to install
            tag: Git tag/commit to checkout (defaults to v{version})

        Returns:
            True if successful, False otherwise
        """
        if tag is None:
            tag = f"v{version}"

        plugin_dir = self.plugins_dir / plugin_slug

        # Remove existing installation if present
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        # Create plugins directory if needed
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clone repository
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", tag, repo_url, str(plugin_dir)]
            result = subprocess.run(clone_cmd, check=True, capture_output=True, text=True)

            # Verify plugin has src directory
            src_dir = plugin_dir / "src"
            if not src_dir.exists() or not src_dir.is_dir():
                shutil.rmtree(plugin_dir)
                return False

            return True
        except subprocess.CalledProcessError as e:
            # Cleanup on failure
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            print(f"Error cloning {plugin_slug}: {e}")
            if e.stderr:
                print(e.stderr)
            return False

    def remove_plugin(self, plugin_slug: str) -> bool:
        """
        Remove an installed plugin.

        Args:
            plugin_slug: Slug of the plugin to remove

        Returns:
            True if removed, False if not found
        """
        plugin_dir = self.plugins_dir / plugin_slug
        if not plugin_dir.exists():
            return False

        try:
            shutil.rmtree(plugin_dir)
            return True
        except OSError as e:
            print(f"Error removing {plugin_slug}: {e}")
            return False

    def get_plugin_commit(self, plugin_slug: str) -> Optional[str]:
        """
        Get the current commit SHA of an installed plugin.

        Args:
            plugin_slug: Slug of the plugin

        Returns:
            Commit SHA, or None if not found
        """
        plugin_dir = self.plugins_dir / plugin_slug
        if not plugin_dir.exists():
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=plugin_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def link_plugin(self, plugin_slug: str, local_path: str) -> bool:
        """
        Link a plugin from a local directory by creating a symlink.

        Args:
            plugin_slug: Slug of the plugin
            local_path: Local directory path to link from

        Returns:
            True if successful, False otherwise
        """
        local_path_obj = Path(local_path)
        
        # Validate local path exists and is a directory
        if not local_path_obj.exists():
            print(f"Error: Path does not exist: {local_path}", file=sys.stderr)
            return False
        
        if not local_path_obj.is_dir():
            print(f"Error: Path is not a directory: {local_path}", file=sys.stderr)
            return False
        
        # Validate src directory exists
        src_dir = local_path_obj / "src"
        if not src_dir.exists() or not src_dir.is_dir():
            print(f"Error: Plugin directory must contain a 'src' directory: {local_path}", file=sys.stderr)
            return False
        
        plugin_dir = self.plugins_dir / plugin_slug
        
        # Remove existing installation if present
        if plugin_dir.exists():
            if plugin_dir.is_symlink():
                plugin_dir.unlink()
            else:
                shutil.rmtree(plugin_dir)
        
        # Create plugins directory if needed
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Convert to absolute path for symlink
            absolute_local_path = local_path_obj.resolve()
            
            # Create symlink
            plugin_dir.symlink_to(absolute_local_path)
            
            return True
        except OSError as e:
            print(f"Error creating symlink for {plugin_slug}: {e}", file=sys.stderr)
            return False

    def is_plugin_installed(self, plugin_slug: str) -> bool:
        """
        Check if a plugin is installed.

        Args:
            plugin_slug: Slug of the plugin

        Returns:
            True if installed, False otherwise
        """
        plugin_dir = self.plugins_dir / plugin_slug
        src_dir = plugin_dir / "src"
        return plugin_dir.exists() and src_dir.exists() and src_dir.is_dir()

