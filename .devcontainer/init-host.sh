#!/usr/bin/env bash
# Ensure host directories exist for devcontainer bind mounts.
# Runs on the host via initializeCommand before container creation.
# Prevents bind mount failures when tools aren't installed on the host.
set -e

home="${HOME:-$USERPROFILE}"

mkdir -p "$home/.codex"
mkdir -p "$home/.claude"
[ -f "$home/.claude.json" ] || echo '{}' > "$home/.claude.json"
