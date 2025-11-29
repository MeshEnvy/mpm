# Mesh Plugin Manager (MPM)

A lightweight package manager for Meshtastic plugins with dependency resolution, version management, and lockfile support.

## Features

- Install and manage Meshtastic plugins from a remote registry
- Automatic dependency resolution with SemVer support
- Lockfile generation for reproducible builds
- Protobuf file generation for plugins
- PlatformIO build system integration

## Installation

```bash
pip install -e .
```

## Usage

```bash
# List installed plugins
mpm list

# List all available plugins from registry
mpm list --all

# Install a plugin
mpm install <slug>

# Install all plugins from meshtastic.json
mpm install

# Remove a plugin
mpm remove <slug>

# Generate protobuf files for all plugins
mpm proto
```

## Development

This package is used by the Meshtastic firmware build system to manage plugins during compilation.

