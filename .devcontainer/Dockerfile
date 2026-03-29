FROM node:22-bookworm

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest
ARG USERNAME=dev

# System packages: dev tools + build essentials for Rust crates with C deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    less procps sudo fzf zsh man-db unzip gnupg2 jq nano vim \
    build-essential pkg-config libssl-dev clang mold \
    openjdk-17-jdk-headless \
    tesseract-ocr tesseract-ocr-deu tesseract-ocr-ara \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/zsh -G sudo $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Persist bash/zsh history
RUN mkdir /commandhistory \
    && touch /commandhistory/.zsh_history \
    && chown -R $USERNAME /commandhistory

# Create workspace and config directories
RUN mkdir -p /workspace /home/$USERNAME/.claude /home/$USERNAME/.codex \
    && chown -R $USERNAME:$USERNAME /workspace /home/$USERNAME/.claude /home/$USERNAME/.codex

# Ensure npm global directory is writable
RUN mkdir -p /usr/local/share/npm-global \
    && chown -R $USERNAME:$USERNAME /usr/local/share/npm-global

ENV DEVCONTAINER=true

# System-level git config survives the bind-mounted ~/.gitconfig from the host
RUN git config --system --add safe.directory /workspace/iscc-tika

WORKDIR /workspace

# Switch to non-root user for remaining installs
USER $USERNAME
ENV HOME=/home/$USERNAME
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH="$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/share/npm-global/bin:$PATH"
ENV SHELL=/bin/zsh

# Pre-create volume mount-point directories so named volumes inherit dev ownership
RUN mkdir -p $HOME/.venvs/iscc-tika $HOME/.cargo/registry $HOME/.cargo/git $HOME/.gradle

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    --default-toolchain stable --profile default

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python 3.13 via uv
RUN uv python install 3.13

# Install maturin for building Python bindings (via uv/pip, not cargo,
# to avoid yanked transitive dependency issues with cargo-xwin/xwin)
RUN uv tool install maturin

# Install mise (task runner)
RUN curl https://mise.run | sh

# Install Claude Code and Codex CLI
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} @openai/codex

# Configure ZSH
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended \
    && echo 'export HISTFILE=/commandhistory/.zsh_history' >> $HOME/.zshrc \
    && echo 'eval "$($HOME/.local/bin/mise activate zsh)"' >> $HOME/.zshrc

# Git defaults (overridden at runtime by bind-mounted ~/.gitconfig from host,
# but useful when the container runs without the bind mount)
RUN git config --global init.defaultBranch main \
    && git config --global core.autocrlf input
