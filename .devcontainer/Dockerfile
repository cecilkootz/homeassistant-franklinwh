FROM mcr.microsoft.com/devcontainers/python:3.13

ARG CLAUDE_CODE_VERSION=latest

# Install Node.js 20, gh, firewall tools, and utilities
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends \
      nodejs \
      gh \
      iptables \
      ipset \
      iproute2 \
      dnsutils \
      aggregate \
      jq \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up npm global prefix accessible to vscode user
RUN mkdir -p /usr/local/share/npm-global && \
    chown -R vscode:vscode /usr/local/share/npm-global

ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin
ENV DEVCONTAINER=true

# Create .claude config dir
RUN mkdir -p /home/vscode/.claude && \
    chown -R vscode:vscode /home/vscode/.claude

# Install Claude Code as vscode user
USER vscode
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# Copy and set up firewall script
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh && \
    echo "vscode ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/vscode-firewall && \
    chmod 0440 /etc/sudoers.d/vscode-firewall
USER vscode
