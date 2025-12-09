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
pip install mesh-plugin-manager
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

## Why aren't we using PlatformIO's package management system?

* Libraries are very slow to install using `pio pkg install` because they install ONCE for EVERY environment target. We don't need that capability.
* MPM can add security features such as enforcing signed releases and revoking bad releases (refusing to compile)
* MPM can enforce Meshtastic-specific target environment compatibility and refuse to compile plugins into targets that will not work.
* MPM can maintain a Meshtastic-specific plugin registry where plugin discovery is easier and publishing is faster due to a streamlined approval process.