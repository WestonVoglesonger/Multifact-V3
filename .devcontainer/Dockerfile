FROM ubuntu:22.04

ENV TZ=America/New_York
ENV DEBIAN_FRONTEND=noninteractive

# Install initial packages
RUN apt-get update && apt-get install --yes \
    apt-transport-https \
    ca-certificates \
    curl \
    debian-keyring \
    debian-archive-keyring \
    git \
    gnupg \
    locales \
    postgresql-client \
    software-properties-common \
    sudo \
    tzdata \
    wget \
    zsh \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir /workspace
WORKDIR /workspace

# Add Caddy repository and GPG keys
RUN apt-get update && apt-get install --yes debian-keyring debian-archive-keyring apt-transport-https && rm -rf /var/lib/apt/lists/*
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list

# Install Caddy
RUN apt-get update && apt-get install --yes caddy && rm -rf /var/lib/apt/lists/*

# Install Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install --yes \
       python3.11 \
       python3-pip \
       libpq-dev \
       python3.11-dev \
    && rm -rf /var/lib/apt/lists/* \
    && unlink /usr/bin/python3 \
    && ln -s /usr/bin/python3.11 /usr/bin/python3

# Install a modern Node.js version from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (as root)
COPY backend/requirements.txt /workspace/backend/requirements.txt
WORKDIR /workspace/backend
RUN pip3 install --no-cache-dir -r requirements.txt

WORKDIR /workspace

# Create and switch to a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
 && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /usr/bin/zsh \
 && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
 && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
ENV HOME /home/$USERNAME

# Install oh-my-zsh
RUN curl https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh | bash - \
 && sed -i 's/robbyrussell/kennethreitz/g' ~/.zshrc \
 && echo 'export PATH=$PATH:$HOME/.local/bin' >>~/.zshrc

# Switch back to root to generate locale and adjust permissions
USER root
RUN locale-gen en_US.UTF-8

# Install the 'oc' CLI
RUN arch="$(arch)"; \
 case "$arch" in \
   x86_64) TARGET='' ;; \
   aarch64) TARGET='arm64-' ;; \
 esac; \
 wget -O /tmp/oc.tgz "https://github.com/okd-project/okd/releases/download/4.14.0-0.okd-2023-12-01-225814/openshift-client-linux-${TARGET}4.14.0-0.okd-2023-12-01-225814.tar.gz" \
 && cd /tmp \
 && tar -xvzf oc.tgz \
 && mv oc /usr/bin/oc \
 && rm kubectl oc.tgz README.md

# Ensure vscode user owns /workspace
RUN chown -R $USERNAME:$USERNAME /workspace

USER $USERNAME
WORKDIR /workspace

# Install Node.js dependencies
COPY package.json package-lock.json /workspace/
USER root
RUN chown -R vscode:vscode /workspace
USER vscode
RUN sudo npm install -g typescript


EXPOSE 1460 1461 1462
