FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    curl \
    postgresql-client \
    zsh \
    nodejs \
    npm \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && npm install -g typescript \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /usr/bin/zsh \
    && mkdir -p /workspace \
    && chown $USERNAME:$USERNAME /workspace

# Set up the workspace
WORKDIR /workspace
USER $USERNAME

# Install Oh My Zsh and configure it
RUN curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh | bash - \
    && sed -i 's/robbyrussell/kennethreitz/g' ~/.zshrc

# Install Python tools
ENV PATH="/home/$USERNAME/.local/bin:$PATH"
RUN pip install --user pipx \
    && pipx ensurepath \
    && pipx install pre-commit \
    && pipx install black \
    && pipx install mypy \
    && pipx install pytest

# The command to run when the container starts
CMD ["sleep", "infinity"]
