#!/usr/bin/env bash
set -e # Exit immediately if a command exits with a non-zero status.

INSTALL_TYPE=""

if [ "$1" == "--global" ]; then
    INSTALL_TYPE="global"
elif [ "$1" == "--user" ]; then
    INSTALL_TYPE="user"
else
    echo "Error: You must specify either --user or --global for Neovim installation."
    echo "Usage: $0 [--user|--global]"
    exit 1
fi

# Use a temporary directory for downloads
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Fetching latest Neovim release information..."
# Use curl to follow redirects and get the latest release URL
LATEST_URL=$(curl -Ls -o /dev/null -w %{url_effective} https://github.com/neovim/neovim/releases/latest)
LATEST_TAG=$(basename "$LATEST_URL")

echo "Downloading Neovim ($LATEST_TAG)..."
wget --quiet "https://github.com/neovim/neovim/releases/download/$LATEST_TAG/nvim-linux64.tar.gz"

echo "Extracting archive..."
tar xzf nvim-linux64.tar.gz

if [ "$INSTALL_TYPE" == "global" ]; then
    echo "Installing Neovim globally..."
    if [ "$(id -u)" -ne 0 ]; then
        echo "Error: Global installation requires root privileges. Please run with sudo."
        exit 1
    fi
    # Ensure target directories exist
    mkdir -p /opt/nvim
    # Remove existing installation
    rm -rf /opt/nvim/*
    # Move files
    mv nvim-linux64/* /opt/nvim/
    # Create symlink
    ln -sf /opt/nvim/bin/nvim /usr/local/bin/nvim
    echo "Neovim installed globally."
    echo "Executable is at /usr/local/bin/nvim"
else # INSTALL_TYPE is "user"
    echo "Installing Neovim for current user..."
    # Ensure target directories exist
    mkdir -p "$HOME/.local/share/nvim"
    mkdir -p "$HOME/.local/bin"
    # Remove existing installation
    rm -rf "$HOME/.local/share/nvim/*"
    # Move files
    mv nvim-linux64/* "$HOME/.local/share/nvim/"
    # Create symlink
    ln -sf "$HOME/.local/share/nvim/bin/nvim" "$HOME/.local/bin/nvim"
    echo "Neovim installed for the current user."
    echo "Executable is at $HOME/.local/bin/nvim"
    echo "Please ensure '$HOME/.local/bin' is in your PATH."
fi

echo "Cleaning up..."
rm -rf "$TMP_DIR"

echo "Neovim installation complete."