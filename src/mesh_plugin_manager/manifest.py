"""Manifest file management for meshtastic.json and meshtastic-lock.json."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ManifestManager:
    """Manages reading and writing manifest files."""

    def __init__(self, project_dir: str):
        """
        Initialize manifest manager.

        Args:
            project_dir: Root directory of the project (where platformio.ini is)
        """
        self.project_dir = Path(project_dir)
        self.manifest_path = self.project_dir / "meshtastic.json"
        self.lockfile_path = self.project_dir / "meshtastic-lock.json"

    def read_manifest(self) -> Dict[str, Any]:
        """
        Read the root meshtastic.json file.

        Returns:
            Dict containing manifest data, or empty dict with defaults if file doesn't exist
        """
        if not self.manifest_path.exists():
            return {"name": "meshtastic-firmware", "plugins": {}}

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_manifest(self, manifest: Dict[str, Any]) -> None:
        """
        Write the root meshtastic.json file.

        Args:
            manifest: Manifest data to write
        """
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def read_lockfile(self) -> Dict[str, Any]:
        """
        Read the meshtastic-lock.json file.

        Returns:
            Dict containing lockfile data, or empty dict if file doesn't exist
        """
        if not self.lockfile_path.exists():
            return {"plugins": {}}

        with open(self.lockfile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_lockfile(self, lockfile: Dict[str, Any]) -> None:
        """
        Write the meshtastic-lock.json file.

        Args:
            lockfile: Lockfile data to write
        """
        with open(self.lockfile_path, "w", encoding="utf-8") as f:
            json.dump(lockfile, f, indent=2, ensure_ascii=False)

    def get_plugin_manifest(self, plugin_slug: str) -> Optional[Dict[str, Any]]:
        """
        Read a plugin's meshtastic.json file.

        Args:
            plugin_slug: Slug of the plugin

        Returns:
            Dict containing plugin manifest, or None if not found
        """
        plugin_dir = self.project_dir / "plugins" / plugin_slug
        manifest_file = plugin_dir / "meshtastic.json"

        if not manifest_file.exists():
            return None

        with open(manifest_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def add_dependency(self, plugin_slug: str, version_spec: str) -> None:
        """
        Add a dependency to the root manifest.

        Args:
            plugin_slug: Slug of the plugin
            version_spec: Version specification (e.g., "^1.0.0")
        """
        manifest = self.read_manifest()
        if "plugins" not in manifest:
            manifest["plugins"] = {}
        manifest["plugins"][plugin_slug] = version_spec
        self.write_manifest(manifest)

    def remove_dependency(self, plugin_slug: str) -> bool:
        """
        Remove a dependency from the root manifest.

        Args:
            plugin_slug: Slug of the plugin to remove

        Returns:
            True if removed, False if not found
        """
        manifest = self.read_manifest()
        if "plugins" in manifest and plugin_slug in manifest["plugins"]:
            del manifest["plugins"][plugin_slug]
            self.write_manifest(manifest)
            return True
        return False

    def update_lockfile_plugin(
        self,
        plugin_slug: str,
        version: str,
        repo: str,
        resolved: str,
        dependencies: Dict[str, str],
        transitive: bool = False,
    ) -> None:
        """
        Update a plugin entry in the lockfile.

        Args:
            plugin_slug: Slug of the plugin
            version: Resolved version
            repo: Repository URL
            resolved: Resolved commit/tag SHA
            dependencies: Dict of dependency slugs to version specs
            transitive: Whether this is a transitive dependency
        """
        lockfile = self.read_lockfile()
        if "plugins" not in lockfile:
            lockfile["plugins"] = {}

        lockfile["plugins"][plugin_slug] = {
            "version": version,
            "repo": repo,
            "resolved": resolved,
            "dependencies": dependencies,
        }
        if transitive:
            lockfile["plugins"][plugin_slug]["transitive"] = True

        self.write_lockfile(lockfile)

    def remove_lockfile_plugin(self, plugin_slug: str) -> bool:
        """
        Remove a plugin from the lockfile.

        Args:
            plugin_slug: Slug of the plugin to remove

        Returns:
            True if removed, False if not found
        """
        lockfile = self.read_lockfile()
        if "plugins" in lockfile and plugin_slug in lockfile["plugins"]:
            del lockfile["plugins"][plugin_slug]
            self.write_lockfile(lockfile)
            return True
        return False

