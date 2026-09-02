#!/usr/bin/env bash
set -e # Exit immediately if a command exits with a non-zero status.

# Grammar repos for languages Neovim doesn't bundle natively (only c, lua,
# markdown, markdown_inline, vim, query, vimdoc ship with core Neovim 0.12+).
# Format: [lang]="git_url[#subdir]" - subdir is used for monorepos like
# tree-sitter-typescript (typescript/tsx) and tree-sitter-php (php/php_only).
declare -A TS_GRAMMARS=(
    [bash]="https://github.com/tree-sitter/tree-sitter-bash"
    [html]="https://github.com/tree-sitter/tree-sitter-html"
    [yaml]="https://github.com/tree-sitter-grammars/tree-sitter-yaml"
    [javascript]="https://github.com/tree-sitter/tree-sitter-javascript"
    [typescript]="https://github.com/tree-sitter/tree-sitter-typescript#typescript"
    [tsx]="https://github.com/tree-sitter/tree-sitter-typescript#tsx"
    [vue]="https://github.com/tree-sitter-grammars/tree-sitter-vue"
    [json]="https://github.com/tree-sitter/tree-sitter-json"
    [php]="https://github.com/tree-sitter/tree-sitter-php#php"
    [blade]="https://github.com/KaranAhlawat/tree-sitter-blade" # NOTE: upstream marks this EXPERIMENTAL
    [rust]="https://github.com/tree-sitter/tree-sitter-rust"
    [toml]="https://github.com/tree-sitter/tree-sitter-toml"
)
TS_CLI_MIN_VERSION="0.26.1"
PARSER_DIR="$HOME/.local/share/nvim/site/parser"

# Languages actually wired up via vim.treesitter.start() in
# nvim/lua/andres/autocmds.lua. Deliberately excludes markdown (Neovim 0.12
# ships its own correct native query; nvim-treesitter's old copy uses a
# predicate broken on 0.12) and blade (not attached to any real filetype -
# .blade.php currently maps to filetype "php", see nvim/lua/andres/remap.lua).
TS_QUERY_LANGS=(bash html yaml javascript typescript tsx vue json php rust toml)
QUERY_DIR="$HOME/.local/share/nvim/site/queries"

install_parsers() {
    shift # drop the leading --parsers
    mkdir -p "$PARSER_DIR"

    if ! command -v tree-sitter >/dev/null 2>&1; then
        echo "tree-sitter-cli not found. Installing via pacman..."
        sudo pacman -S --needed tree-sitter-cli
    fi
    local ts_version
    ts_version=$(tree-sitter --version | awk '{print $2}')
    if [ "$(printf '%s\n%s' "$TS_CLI_MIN_VERSION" "$ts_version" | sort -V | head -1)" != "$TS_CLI_MIN_VERSION" ]; then
        echo "Error: tree-sitter-cli $ts_version is older than the required $TS_CLI_MIN_VERSION."
        echo "Update it via: sudo pacman -S tree-sitter-cli"
        return 1
    fi
    echo "Using tree-sitter-cli $ts_version"

    local langs=("$@")
    if [ ${#langs[@]} -eq 0 ]; then
        langs=("${!TS_GRAMMARS[@]}")
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "$tmp_dir"' RETURN

    for lang in "${langs[@]}"; do
        local spec="${TS_GRAMMARS[$lang]:-}"
        if [ -z "$spec" ]; then
            echo "Skipping '$lang': no known grammar repo configured in TS_GRAMMARS."
            continue
        fi

        local repo_url="${spec%%#*}"
        local subdir=""
        [[ "$spec" == *#* ]] && subdir="${spec##*#}"

        echo "=== $lang ($repo_url${subdir:+ [$subdir]}) ==="
        local clone_dir="$tmp_dir/$lang"
        if ! git clone --depth 1 --recurse-submodules --shallow-submodules "$repo_url" "$clone_dir"; then
            echo "Failed to clone $repo_url, skipping $lang."
            continue
        fi

        local build_dir="$clone_dir"
        [ -n "$subdir" ] && build_dir="$clone_dir/$subdir"

        if [ -f "$clone_dir/package.json" ]; then
            if ! (cd "$clone_dir" && npm install --ignore-scripts --no-audit --no-fund --silent); then
                echo "Failed to npm install for $lang, skipping."
                continue
            fi
        fi

        if ! (cd "$build_dir" && tree-sitter generate && tree-sitter build); then
            echo "Failed to build $lang, skipping."
            continue
        fi

        local so_file
        so_file=$(find "$build_dir" -maxdepth 1 -iname "*.so" | head -1)
        if [ -z "$so_file" ]; then
            echo "No .so produced for $lang, skipping."
            continue
        fi
        cp "$so_file" "$PARSER_DIR/$lang.so"
        echo "Installed $PARSER_DIR/$lang.so"
    done

    echo ""
    echo "Parser binaries installed to $PARSER_DIR (already on Neovim's native runtimepath)."
    echo "NOTE: this only builds the parser binaries. Highlight/indent query files"
    echo "(highlights.scm etc.) are a separate step, not something tree-sitter-cli produces."
}

install_queries() {
    shift # drop the leading --queries
    mkdir -p "$QUERY_DIR"

    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "$tmp_dir"' RETURN

    echo "Cloning nvim-treesitter (master, archived/frozen) for its query files..."
    if ! git clone --quiet --depth 1 --branch master \
        https://github.com/nvim-treesitter/nvim-treesitter "$tmp_dir/nvim-treesitter"; then
        echo "Failed to clone nvim-treesitter, aborting."
        return 1
    fi

    local langs=("$@")
    if [ ${#langs[@]} -eq 0 ]; then
        langs=("${TS_QUERY_LANGS[@]}")
    fi

    for lang in "${langs[@]}"; do
        local src="$tmp_dir/nvim-treesitter/queries/$lang"
        if [ ! -d "$src" ]; then
            echo "Skipping '$lang': no query dir found upstream."
            continue
        fi
        mkdir -p "$QUERY_DIR/$lang"
        cp "$src/"*.scm "$QUERY_DIR/$lang/" 2>/dev/null
        echo "Installed queries for $lang: $(ls "$QUERY_DIR/$lang" | tr '\n' ' ')"
    done

    echo ""
    echo "Query files installed to $QUERY_DIR (already on Neovim's native runtimepath)."
}

if [ "$1" == "--parsers" ]; then
    install_parsers "$@"
    exit 0
fi

if [ "$1" == "--queries" ]; then
    install_queries "$@"
    exit 0
fi

INSTALL_TYPE=""

if [ "$1" == "--global" ]; then
    INSTALL_TYPE="global"
elif [ "$1" == "--user" ]; then
    INSTALL_TYPE="user"
else
    echo "Error: You must specify either --user or --global for Neovim installation."
    echo "Usage: $0 [--user|--global] [--force]"
    echo "       $0 --parsers [lang ...]   (build missing treesitter parsers; default: all configured languages)"
    echo "       $0 --queries [lang ...]   (fetch highlight/indent query files; default: all configured languages)"
    exit 1
fi

if command -v nvim >/dev/null 2>&1 && [ "$2" != "--force" ]; then
    echo "Neovim is already installed at: $(command -v nvim)"
    echo "Version: $(nvim --version | head -1)"
    echo ""
    echo "Skipping install so this script doesn't shadow it with a separate build/alias."
    echo "Re-run as: $0 $1 --force  to install the latest release anyway."
    exit 0
fi

# Use a temporary directory for downloads
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Fetching latest Neovim release information..."
# Use curl to follow redirects and get the latest release URL
LATEST_URL=$(curl -Ls -o /dev/null -w %{url_effective} https://github.com/neovim/neovim/releases/latest)
LATEST_TAG=$(basename "$LATEST_URL")

echo "Downloading Neovim ($LATEST_TAG)..."
wget --quiet "https://github.com/neovim/neovim/releases/download/$LATEST_TAG/nvim-linux-x86_64.tar.gz"

echo "Extracting archive..."
tar xzf nvim-linux-x86_64.tar.gz

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
    mv nvim-linux-x86_64/* /opt/nvim/
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
    rm -rf "$HOME/.local/share/nvim"/*
    # Move files
    mv nvim-linux-x86_64/* "$HOME/.local/share/nvim/"
    # Create symlink
    ln -sf "$HOME/.local/share/nvim/bin/nvim" "$HOME/.local/bin/nvim"
    echo "Neovim installed for the current user."
    echo "Executable is at $HOME/.local/bin/nvim"
    echo "Please ensure '$HOME/.local/bin' is in your PATH."
fi

# Set up alias in .bashrc.local
# If running with sudo, we want the non-root user's HOME
ACTUAL_HOME=$HOME
if [ -n "$SUDO_USER" ]; then
    ACTUAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
fi

BASHRC_LOCAL="$ACTUAL_HOME/.bashrc.local"
NVIM_EXE=""
if [ "$INSTALL_TYPE" == "global" ]; then
    NVIM_EXE="/usr/local/bin/nvim"
else
    NVIM_EXE="$ACTUAL_HOME/.local/bin/nvim"
fi

echo "Setting up Neovim alias in $BASHRC_LOCAL..."
touch "$BASHRC_LOCAL"
# Remove existing nvim aliases to avoid duplicates
if [ -f "$BASHRC_LOCAL" ]; then
    # We use a temporary file to avoid issues with redirecting to the same file
    sed "/alias nvim=/d" "$BASHRC_LOCAL" | sed "/alias vim='nvim'/d" > "$BASHRC_LOCAL.tmp"
    mv "$BASHRC_LOCAL.tmp" "$BASHRC_LOCAL"
fi
echo "alias nvim='$NVIM_EXE'" >> "$BASHRC_LOCAL"
echo "alias vim='nvim'" >> "$BASHRC_LOCAL"
# Ensure the user owns their .bashrc.local if we created/modified it as root
if [ -n "$SUDO_USER" ]; then
    chown "$SUDO_USER":"$(id -gn "$SUDO_USER")" "$BASHRC_LOCAL"
fi

echo "Cleaning up..."
rm -rf "$TMP_DIR"

echo "Neovim installation complete."
