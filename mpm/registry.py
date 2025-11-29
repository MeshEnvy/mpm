"""Registry client for fetching plugin information."""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests


class RegistryClient:
    """Client for fetching and caching plugin registry."""

    REGISTRY_URL = "https://registry.meshforge.org/registry.json"
    CACHE_DURATION = 3600  # 1 hour in seconds

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize registry client.

        Args:
            cache_dir: Directory for caching registry data (defaults to temp directory)
        """
        if cache_dir is None:
            import tempfile

            cache_dir = tempfile.gettempdir()
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "mpm-registry-cache.json"
        self.cache_timestamp_file = self.cache_dir / "mpm-registry-cache-timestamp.txt"

    def _is_cache_valid(self) -> bool:
        """Check if the cached registry is still valid."""
        if not self.cache_file.exists() or not self.cache_timestamp_file.exists():
            return False

        try:
            with open(self.cache_timestamp_file, "r", encoding="utf-8") as f:
                timestamp = float(f.read().strip())
            return (time.time() - timestamp) < self.CACHE_DURATION
        except (ValueError, IOError):
            return False

    def _read_cache(self) -> Optional[Dict[str, Any]]:
        """Read registry from cache."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _write_cache(self, data: Dict[str, Any]) -> None:
        """Write registry to cache."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            with open(self.cache_timestamp_file, "w", encoding="utf-8") as f:
                f.write(str(time.time()))
        except IOError:
            # Ignore cache write failures
            pass

    def fetch_registry(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Fetch the plugin registry from remote or cache.

        Args:
            force_refresh: If True, ignore cache and fetch fresh data

        Returns:
            Dict containing registry data

        Raises:
            requests.RequestException: If registry fetch fails
        """
        # Check cache first unless force refresh
        if not force_refresh and self._is_cache_valid():
            cached = self._read_cache()
            if cached is not None:
                return cached

        # Fetch from remote
        try:
            response = requests.get(self.REGISTRY_URL, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Write to cache
            self._write_cache(data)

            return data
        except requests.RequestException as e:
            # If fetch fails, try cache even if stale
            cached = self._read_cache()
            if cached is not None:
                return cached
            raise

    def get_plugin_info(self, plugin_slug: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific plugin from the registry.

        Args:
            plugin_slug: Slug of the plugin
            force_refresh: If True, ignore cache

        Returns:
            Dict containing plugin info, or None if not found
        """
        registry = self.fetch_registry(force_refresh=force_refresh)
        return registry.get(plugin_slug)

    def list_plugins(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        List all plugins in the registry.

        Args:
            force_refresh: If True, ignore cache

        Returns:
            Dict mapping plugin slugs to their info
        """
        return self.fetch_registry(force_refresh=force_refresh)

