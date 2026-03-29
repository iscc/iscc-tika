#!/usr/bin/env bash
# Install development tools and set up quality gates.
set -e

echo "setup-dev: installing dev tools..."
uv tool install prek
uv tool install ruff
uv tool install taplo
uv tool install yamlfix
uv tool install mdformat --with 'mdformat-mkdocs[recommended]'

echo "setup-dev: trusting mise configuration..."
mise trust --yes 2>/dev/null || true

echo "setup-dev: installing git hooks..."
# prek >=0.3.6 treats chmod failures as hard errors.  The .git directory lives
# on a bind mount from the Windows host where chmod is not supported.  We use
# --git-dir to redirect hook shims to a container-local directory and tell git
# to look there via core.hooksPath.
HOOKS_GIT_DIR="$HOME/.git-hooks"
mkdir -p "$HOOKS_GIT_DIR/hooks"
git config core.hooksPath "$HOOKS_GIT_DIR/hooks"
prek install --hook-type pre-commit --hook-type pre-push --git-dir "$HOOKS_GIT_DIR"

echo "setup-dev: done"
