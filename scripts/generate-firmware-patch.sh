#!/usr/bin/env bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the script directory and repo root
# Script is at vendor/mpm/scripts/generate-firmware-patch.sh
# Repo root is two levels up
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIRMWARE_DIR="$VENDOR_ROOT/firmware"
PATCH_DIR="$VENDOR_ROOT/mpm/src/mesh_plugin_manager/patches"

echo "Generating firmware patch..."

# Check if vendor/firmware exists
if [ ! -d "$FIRMWARE_DIR" ]; then
  echo -e "${RED}Error: vendor/firmware directory not found${NC}"
  exit 1
fi

cd "$FIRMWARE_DIR"

# Check if this is a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo -e "${RED}Error: vendor/firmware is not a git repository${NC}"
  exit 1
fi

# Get current branch/tag name to determine patch filename
BRANCH_OR_TAG=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || git describe --exact-match --tags HEAD 2>/dev/null || echo "")
if [ -z "$BRANCH_OR_TAG" ] || [ "$BRANCH_OR_TAG" = "HEAD" ]; then
  # Try to get tag from describe
  BRANCH_OR_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
fi

# Determine patch filename
if [ -n "$BRANCH_OR_TAG" ]; then
  CLEAN_NAME=$(echo "$BRANCH_OR_TAG" | sed 's/^v//')
  # Check if it's a version tag (e.g., 2.6.13) or a branch name (e.g., develop)
  if [[ "$CLEAN_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    PATCH_FILE="$PATCH_DIR/firmware-patch-v${CLEAN_NAME}.diff"
  else
    PATCH_FILE="$PATCH_DIR/firmware-patch-${CLEAN_NAME}.diff"
  fi
else
  PATCH_FILE="$PATCH_DIR/firmware-patch.diff"
fi

echo "Branch/tag: ${BRANCH_OR_TAG:-unknown}"
echo "Patch file: $PATCH_FILE"

# Reset to clean state (discard any existing patch changes)
echo "Resetting to clean state..."
git reset --hard HEAD
git clean -fd

# Apply the patch using mpm init
echo "Applying patch with mpm init..."
mpm init

# Generate the patch from staged and unstaged changes
echo "Generating patch file..."
git diff HEAD > "$PATCH_FILE"

if [ $? -eq 0 ]; then
  PATCH_SIZE=$(wc -l < "$PATCH_FILE")
  if [ "$PATCH_SIZE" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Patch file is empty. No changes detected.${NC}"
  else
    echo -e "${GREEN}Successfully generated $(basename "$PATCH_FILE") (${PATCH_SIZE} lines)${NC}"
  fi
else
  echo -e "${RED}Error: Failed to generate patch file${NC}"
  exit 1
fi
