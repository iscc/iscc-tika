#!/usr/bin/env bash
# Configure Codex CLI for devcontainer use.
# Ensures file-based credential storage so auth tokens persist via bind mount.
set -e

config="$HOME/.codex/config.toml"

# Create config.toml if missing
if [ ! -f "$config" ]; then
    cat > "$config" << 'TOML'
# Force file-based credential storage for devcontainer bind mount compatibility.
# OS keyring credentials don't transfer across bind mounts.
cli_auth_credentials_store = "file"
TOML
    echo "codex: created $config with file-based credential storage"
elif ! grep -q 'cli_auth_credentials_store' "$config"; then
    # Append setting if config exists but doesn't configure credential storage
    printf '\n# Force file-based credential storage for devcontainer bind mount compatibility.\ncli_auth_credentials_store = "file"\n' >> "$config"
    echo "codex: added file-based credential storage to $config"
elif grep -q 'cli_auth_credentials_store.*=.*"keyring"' "$config"; then
    echo "codex: WARNING — cli_auth_credentials_store is set to \"keyring\" in $config"
    echo "codex: keyring credentials don't transfer via bind mount; run 'codex login --device-auth' if needed"
fi

# Check auth status
if [ -f "$HOME/.codex/auth.json" ] && [ -s "$HOME/.codex/auth.json" ]; then
    echo "codex: auth.json found — credentials available"
else
    echo "codex: no credentials found — run 'codex login --device-auth' to authenticate"
fi
