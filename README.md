# Dotfiles

This repository contains my personal dotfiles, managing the configuration for various tools and applications on my Linux system.

## Installation

### Prerequisites

Ensure you have the following tools installed on your system:
*   `git`
*   `curl`
*   `wget`
*   `tar`

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/dotfiles.git ~/.dotfiles # Replace with your actual repo URL
    cd ~/.dotfiles
    ```

2.  **Run the main installation script:**
    This script will symlink various configuration files and handle the installation of Neovim.

    ```bash
    ./install.sh
    ```

    During the execution of `install.sh`, you will be prompted to choose how to install Neovim:
    *   **User-local installation (`--user`):** Neovim will be installed to `$HOME/.local/share/nvim`, and its executable will be symlinked to `$HOME/.local/bin/nvim`. You will need to ensure that `$HOME/.local/bin` is in your system's `PATH` environment variable.
    *   **Global installation (`--global`):** Neovim will be installed to `/opt/nvim`, and its executable will be symlinked to `/usr/local/bin/nvim`. This option requires `sudo` privileges.

    If you skip the Neovim application installation, you can run it manually later:
    *   For user-local: `./install_neovim.sh --user`
    *   For global: `sudo ./install_neovim.sh --global`

### Post-Installation Steps

*   **Vim Plugins:** After the `install.sh` script completes, open Vim and run `:PlugInstall` to install all configured plugins (If needed/wanted, Neovim should install plugins on first run via Lazy)
*   **Neovim `PATH` (for user-local install):** If you chose the user-local installation for Neovim, ensure that `$HOME/.local/bin` is added to your shell's `PATH`. The `install.sh` script should have handled linking your `.bashrc`, which hopefully includes this.

## Repository Structure

*   `.config/`: Contains configurations for applications using the XDG Base Directory Specification (e.g., Alacritty, Dunst, Fish, Hyprland, Polybar, Rofi, Waybar).
*   `bash/`: Bash-related configurations, including `bashrc` and `dircolors`.
*   `bin/`: Custom scripts and executables.
*   `git/`: Git configuration.
*   `misc/`: Miscellaneous files and scripts.
*   `nvim/`: Neovim configuration files.
*   `php/`: PHP-related configurations and scripts.
*   `utils/`: Utility scripts.
*   `vim/`: Legacy Vim configuration files.
*   `install.sh`: The main installation script.
*   `install_neovim.sh`: Script specifically for installing the Neovim application.

This `README.md` aims to make your dotfiles more maintainable and user-friendly.
