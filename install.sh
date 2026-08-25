#!/usr/bin/env bash
set -e # Exit immediately if a command exits with a non-zero status.

# Function to check for command existence
command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# Check for essential commands
echo "Checking for required commands..."
REQUIRED_COMMANDS=("readlink" "dirname" "mv" "ln" "source" "curl" "wget" "tar" "mkdir" "rm")
for cmd in "${REQUIRED_COMMANDS[@]}"; do
  if ! command_exists "$cmd"; then
    echo "Error: Required command '$cmd' is not installed. Please install it and try again."
    exit 1
  fi
done
echo "All required commands found."

# Absolute path to this script. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in. /home/user/bin
SCRIPTPATH=$(dirname "$SCRIPT")

echo "------------------------------------"
echo "Setting up BASH dotfiles..."
mv ~/.bashrc ~/.bashrc.old || true # Use || true to prevent error if file doesn't exist
ln -s "$SCRIPTPATH/bash/bashrc" ~/.bashrc
source ~/.bashrc # Fixed typo here
echo "BASH dotfiles done."

echo "------------------------------------"
echo "Setting up dircolors..."
mv ~/.dircolors ~/.dircolors.old || true
ln -s "$SCRIPTPATH/bash/dircolors" ~/.dircolors
echo "dircolors done."

echo "------------------------------------"
echo "Setting up GIT dotfiles..."
mv ~/.gitconfig ~/.gitconfig.old || true
ln -s "$SCRIPTPATH/git/.gitconfig" ~/.gitconfig
echo "GIT dotfiles done."

echo "------------------------------------"
echo "Setting up .mcphost symlink..."
ln -s "$SCRIPTPATH/.mcphost" ~/.mcphost || true # Symlink might already exist
echo ".mcphost done."

echo "------------------------------------"
echo "Ensuring ~/bin exists (on PATH via bashrc/fish)..."
mkdir -p ~/bin

echo "------------------------------------"
echo "Setting up .config symlinks..."
mkdir -p ~/.config

# Garuda stuff
rm -rf ~/.config/wireplumber || true
ln -s "$SCRIPTPATH/.config/wireplumber" ~/.config/wireplumber
rm -rf ~/.config/waybar || true
ln -s "$SCRIPTPATH/.config/waybar" ~/.config/waybar
rm -rf ~/.config/hypr || true
ln -s "$SCRIPTPATH/.config/hypr" ~/.config/hypr
rm -rf ~/.config/fish || true
ln -s "$SCRIPTPATH/.config/fish" ~/.config/fish
echo ".config symlinks done."

echo "------------------------------------"
echo "Setting up systemd user services..."
if [ -e ~/.config/systemd ] && [ ! -L ~/.config/systemd ]; then
  mv ~/.config/systemd ~/.config/systemd.old
fi
ln -sfn "$SCRIPTPATH/.config/systemd" ~/.config/systemd
systemctl --user daemon-reload
systemctl --user enable --now opencode-serve.service
echo "systemd user services linked and OpenCode server enabled."


echo "------------------------------------"
echo "Setting up Claude Code config..."
mkdir -p ~/.claude
for f in CLAUDE.md RTK.md settings.json statusline-command.sh; do
  rm -f ~/.claude/"$f"
  ln -s "$SCRIPTPATH/claude/$f" ~/.claude/"$f"
done
for d in skills commands agents hooks; do
  rm -rf ~/.claude/"$d"
  ln -s "$SCRIPTPATH/claude/$d" ~/.claude/"$d"
done
echo "Claude Code config linked to ~/.claude."
echo "  - Uses this machine's username in ~/.claude/settings.json's hook paths (/home/andres/...) —"
echo "    if provisioning under a different username, update those paths after linking."

echo "------------------------------------"
echo "Neovim Application Installation"
echo "Do you want to install Neovim for the current user or globally?"
echo "  1) User-local installation (\$HOME/.local/bin/nvim)"
echo "  2) Global installation (/usr/local/bin/nvim - requires sudo)"
read -rp "Please enter 1 or 2: " nvim_choice

NVIM_INSTALL_FLAG=""
if [ "$nvim_choice" == "1" ]; then
    NVIM_INSTALL_FLAG="--user"
    echo "Proceeding with user-local Neovim application installation."
    "$SCRIPTPATH/install_neovim.sh" "$NVIM_INSTALL_FLAG"
elif [ "$nvim_choice" == "2" ]; then
    NVIM_INSTALL_FLAG="--global"
    echo "Proceeding with global Neovim application installation (will prompt for sudo password)."
    sudo "$SCRIPTPATH/install_neovim.sh" "$NVIM_INSTALL_FLAG"
else
    echo "Invalid choice or no choice made. Skipping Neovim application installation."
    echo "You can run '$SCRIPTPATH/install_neovim.sh --user' or 'sudo $SCRIPTPATH/install_neovim.sh --global' manually later."
fi

echo "------------------------------------"
echo "Neovim Configuration Link"
# Link the Neovim configuration directory from your dotfiles
rm -rf ~/.config/nvim || true # Remove old symlink or directory
ln -s "$SCRIPTPATH/nvim" ~/.config/nvim # Create new symlink to dotfiles nvim config
echo "Neovim configuration linked to ~/.config/nvim."
echo "NVIM setup done."

echo

echo "===================================="
echo "All dotfiles setup complete!"
echo "Remember to:"
echo "  - Ensure '$HOME/.local/bin' is in your PATH if you chose user-local Neovim installation."
echo "===================================="
