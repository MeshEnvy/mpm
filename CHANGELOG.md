# Changelog

All notable changes to Meshtastic Plugin Manager (MPM) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Minor
- Added `new` command to create new plugin scaffolding
- Removed `watch` command

### Patch
- Refactored CLI to use self-registering command pattern (each command module registers itself via `register()` function)
- Refactored CLI commands into separate modules (each command now has its own module in `commands/`)
- Updated README with explanation for why PlatformIO's package management system isn't used
- Added changelog documentation
- Updated firmware initializer patch

## [1.5.0] - 2025-12-06

### Patch
- Updated registry path in CLI and changed registry URL in RegistryClient

## [1.4.0] - 2025-12-05

### Patch
- Updated firmware patch
- Fixed CLI command to reference plugin.h instead of meta.h for version bumping
- Fixed header filename construction in dynamic module generation

## [1.3.0] - 2025-12-05

### Minor
- Added 'bump' command to CLI for version management in plugin.h and registry.json
- Added dynamic module generation for plugins and updated CLI command

### Patch
- Removed plugins 'lobbs' and 'lodb' from default registry

## [1.1.3] - 2025-12-04

### Patch
- Updated firmware patch

## [1.1.2] - 2025-12-01

### Patch
- Fixed PluginProvider resolution interface

## [1.1.1] - 2025-11-30

### Patch
- Updated firmware patch

## [1.1.0] - 2025-11-30

### Minor
- Added firmware patching functionality with new CLI commands for plugin management

## [1.0.1] - 2025-11-30

### Patch
- Version bump

## [1.0.0] - 2025-11-30

### Major
- Initial release of Meshtastic Plugin Manager
- Plugin installation and management
- Protobuf generation support
- Build utilities for Meshtastic plugins
- Registry support for plugin discovery

[Unreleased]: https://github.com/MeshEnvy/mpm/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/MeshEnvy/mpm/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/MeshEnvy/mpm/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/MeshEnvy/mpm/compare/v1.1.3...v1.3.0
[1.1.3]: https://github.com/MeshEnvy/mpm/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/MeshEnvy/mpm/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/MeshEnvy/mpm/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/MeshEnvy/mpm/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/MeshEnvy/mpm/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/MeshEnvy/mpm/compare/270a2e9...v1.0.0
