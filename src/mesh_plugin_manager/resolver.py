"""Dependency resolver using resolvelib."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import resolvelib
import semver


class Requirement:
    """Simple requirement object for resolvelib."""

    def __init__(self, identifier: str, spec: str):
        self.identifier = identifier
        self.spec = spec

    def __repr__(self):
        return f"Requirement({self.identifier}@{self.spec})"


class PluginProvider:
    """Provider for resolvelib that handles plugin dependencies."""

    def __init__(
        self,
        registry: Dict[str, Dict[str, Any]],
        project_dir: str,
        temp_dir: Optional[str] = None,
    ):
        """
        Initialize the provider.

        Args:
            registry: Plugin registry data
            project_dir: Root project directory
            temp_dir: Temporary directory for cloning repos during resolution
        """
        self.registry = registry
        self.project_dir = Path(project_dir)
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="mpm-resolve-")
        self.temp_dir = Path(temp_dir)
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}
        self._requirement_specs: Dict[str, str] = {}  # Map identifier to spec
        self._candidate_to_identifier: Dict[str, str] = {}  # Map candidate to identifier

    def identify(self, requirement_or_candidate):
        """
        Return identifier for a requirement or candidate.

        Args:
            requirement_or_candidate: Requirement object, candidate string, or string identifier

        Returns:
            Plugin slug (identifier)
        """
        if isinstance(requirement_or_candidate, Requirement):
            self._requirement_specs[requirement_or_candidate.identifier] = requirement_or_candidate.spec
            return requirement_or_candidate.identifier
        elif isinstance(requirement_or_candidate, str):
            # Could be a candidate (identifier@version) or just an identifier
            if "@" in requirement_or_candidate:
                # Extract identifier from candidate
                return requirement_or_candidate.split("@")[0]
            return requirement_or_candidate
        return str(requirement_or_candidate)

    def get_preference(self, identifier: str, resolutions: Dict[str, str], candidates: List[str], information: List[Dict[str, Any]]) -> str:
        """
        Return preference for candidate selection (prefer latest versions).

        Args:
            identifier: Plugin slug
            resolutions: Current resolutions
            candidates: List of candidate versions
            information: Information about requirements

        Returns:
            Preference value (lower is preferred)
        """
        # Prefer latest versions (reverse sort, so latest comes first)
        candidates_sorted = sorted(candidates, key=lambda v: semver.Version.parse(v), reverse=True)
        if candidates:
            # Return index of candidate (lower index = higher preference)
            return str(candidates_sorted.index(candidates[0]))
        return "0"

    def find_matches(self, identifier: str, requirements, incompatibilities: List[str]) -> List[str]:
        """
        Find matching versions for a plugin.

        Args:
            identifier: Plugin slug
            requirements: Version requirements (from resolvelib)
            incompatibilities: List of incompatible versions

        Returns:
            List of matching version strings (candidates)
        """
        if identifier not in self.registry:
            return []

        plugin_info = self.registry[identifier]
        
        if "version" not in plugin_info:
            return []
        
        available_versions = [plugin_info["version"]]

        # Get version spec from stored requirements or use latest
        version_spec = self._requirement_specs.get(identifier, "*")

        # Filter by requirements
        matching_versions = []
        for version_str in available_versions:
            try:
                version = semver.Version.parse(version_str)
            except ValueError:
                continue

            # Skip incompatibilities (check full candidate format)
            candidate = f"{identifier}@{version_str}"
            if candidate in incompatibilities or version_str in incompatibilities:
                continue

            # Check if version satisfies spec
            if self._satisfies_version(version, version_spec):
                # Store mapping from candidate to identifier
                candidate_str = f"{identifier}@{version_str}"
                self._candidate_to_identifier[candidate_str] = identifier
                matching_versions.append(candidate_str)

        return sorted(
            matching_versions,
            key=lambda v: semver.Version.parse(v.split("@")[1]) if "@" in v else semver.Version.parse(v),
            reverse=True,
        )

    def _satisfies_version(self, version: semver.Version, spec: str) -> bool:
        """
        Check if a version satisfies a version specification.

        Args:
            version: Version to check
            spec: Version specification (e.g., ">=1.0.0", "^1.2.0")

        Returns:
            True if version satisfies spec
        """
        spec = spec.strip()
        if not spec or spec == "*":
            return True

        # Handle caret ranges (^1.2.3 means >=1.2.3 <2.0.0)
        if spec.startswith("^"):
            base_version_str = spec[1:]
            try:
                base_version = semver.Version.parse(base_version_str)
                next_major = base_version.bump_major()
                return version >= base_version and version < next_major
            except ValueError:
                return False

        # Handle tilde ranges (~1.2.3 means >=1.2.3 <1.3.0)
        if spec.startswith("~"):
            base_version_str = spec[1:]
            try:
                base_version = semver.Version.parse(base_version_str)
                next_minor = base_version.bump_minor()
                return version >= base_version and version < next_minor
            except ValueError:
                return False

        # Handle >=, <=, >, <, =
        if spec.startswith(">="):
            try:
                min_version = semver.Version.parse(spec[2:].strip())
                return version >= min_version
            except ValueError:
                return False
        elif spec.startswith("<="):
            try:
                max_version = semver.Version.parse(spec[2:].strip())
                return version <= max_version
            except ValueError:
                return False
        elif spec.startswith(">"):
            try:
                min_version = semver.Version.parse(spec[1:].strip())
                return version > min_version
            except ValueError:
                return False
        elif spec.startswith("<"):
            try:
                max_version = semver.Version.parse(spec[1:].strip())
                return version < max_version
            except ValueError:
                return False
        elif spec.startswith("="):
            try:
                req_version = semver.Version.parse(spec[1:].strip())
                return version == req_version
            except ValueError:
                return False
        else:
            # Exact match
            try:
                req_version = semver.Version.parse(spec)
                return version == req_version
            except ValueError:
                return False

    def get_dependencies(self, candidate: str) -> List:
        """
        Get dependencies for a plugin version candidate.

        Args:
            candidate: Candidate string in format "identifier@version"

        Returns:
            List of Requirement objects representing dependencies
        """
        # Parse candidate to get identifier and version
        if "@" not in candidate:
            return []
        
        identifier, version = candidate.split("@", 1)
        cache_key = f"{identifier}@{version}"
        
        # Check cache first
        if cache_key in self._manifest_cache:
            manifest = self._manifest_cache[cache_key]
            deps = manifest.get("dependencies", {})
            return [Requirement(dep_slug, dep_spec) for dep_slug, dep_spec in deps.items() if dep_slug != "meshtastic"]

        # Try to get from registry first
        if identifier in self.registry:
            plugin_info = self.registry[identifier]
            # Check if this version matches the registry version
            if version == plugin_info.get("version", version):
                if "dependencies" in plugin_info:
                    deps = plugin_info["dependencies"]
                    return [Requirement(dep_slug, dep_spec) for dep_slug, dep_spec in deps.items() if dep_slug != "meshtastic"]

        # Clone repo and read meshtastic.json
        repo_url = None
        tag = None
        if identifier in self.registry:
            plugin_info = self.registry[identifier]
            repo_url = plugin_info.get("repo")
            tag = f"v{version}"

        if not repo_url:
            return []

        # Clone to temp directory
        temp_plugin_dir = self.temp_dir / f"{identifier}-{version}"
        if temp_plugin_dir.exists():
            # Remove if exists
            shutil.rmtree(temp_plugin_dir)

        try:
            # Clone repo
            clone_cmd = ["git", "clone", "--depth", "1", "--branch", tag, repo_url, str(temp_plugin_dir)]
            subprocess.run(clone_cmd, check=True, capture_output=True)

            # Read meshtastic.json
            manifest_file = temp_plugin_dir / "meshtastic.json"
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    self._manifest_cache[cache_key] = manifest
                    deps = manifest.get("dependencies", {})
                    # Filter out meshtastic dependency (it's not a plugin)
                    return [Requirement(dep_slug, dep_spec) for dep_slug, dep_spec in deps.items() if dep_slug != "meshtastic"]
        except (subprocess.CalledProcessError, json.JSONDecodeError, IOError):
            pass

        return []

    def is_satisfied_by(self, requirement, candidate: str) -> bool:
        """
        Check if a candidate version satisfies a requirement.

        Args:
            requirement: Requirement object or identifier
            candidate: Candidate string in format "identifier@version"

        Returns:
            True if candidate satisfies requirement
        """
        # Extract identifier and version from candidate
        if "@" not in candidate:
            return False
        
        candidate_identifier, candidate_version = candidate.split("@", 1)
        
        # Get requirement identifier and spec
        if isinstance(requirement, Requirement):
            req_identifier = requirement.identifier
            req_spec = requirement.spec
        else:
            req_identifier = str(requirement)
            req_spec = self._requirement_specs.get(req_identifier, "*")
        
        # Check identifier matches
        if candidate_identifier != req_identifier:
            return False
        
        # Check version satisfies spec
        try:
            version = semver.Version.parse(candidate_version)
            return self._satisfies_version(version, req_spec)
        except ValueError:
            return False


class DependencyResolver:
    """Resolves plugin dependencies using resolvelib."""

    def __init__(self, registry: Dict[str, Dict[str, Any]], project_dir: str):
        """
        Initialize resolver.

        Args:
            registry: Plugin registry data
            project_dir: Root project directory
        """
        self.registry = registry
        self.project_dir = project_dir
        self.provider = PluginProvider(registry, project_dir)

    def resolve(self, requirements: Dict[str, str]) -> Dict[str, str]:
        """
        Resolve dependencies for a set of requirements.

        Args:
            requirements: Dict mapping plugin slugs to version specs

        Returns:
            Dict mapping plugin slugs to resolved versions

        Raises:
            resolvelib.resolvers.ResolutionImpossible: If dependencies cannot be resolved
        """
        # Create resolver
        reporter = resolvelib.BaseReporter()
        resolver = resolvelib.Resolver(self.provider, reporter)

        # Convert requirements to resolvelib format
        # Create Requirement objects that the provider can identify
        req_list = []
        for identifier, spec in requirements.items():
            req_list.append(Requirement(identifier, spec))

        # Resolve
        result = resolver.resolve(req_list)

        # Extract resolutions
        resolutions: Dict[str, str] = {}
        for requirement, candidate in result.mapping.items():
            # requirement is the identifier, candidate is "identifier@version"
            if isinstance(requirement, Requirement):
                identifier = requirement.identifier
            else:
                identifier = str(requirement)
            
            # Extract version from candidate
            if "@" in candidate:
                _, version = candidate.split("@", 1)
            else:
                version = candidate
            
            resolutions[identifier] = version

        return resolutions

