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
    && rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && mkdir -p /workspace \
    && chown $USERNAME:$USERNAME /workspace

# Set up the workspace
WORKDIR /workspace
USER $USERNAME

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
