#!/usr/bin/env bash
set -eo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/install/lib.sh"

source "$DOTFILES_ROOT/scripts/install/treesitter-versions.sh"

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
    [php_only]="https://github.com/tree-sitter/tree-sitter-php#php_only"
    [css]="https://github.com/tree-sitter/tree-sitter-css"
    [blade]="https://github.com/EmranMR/tree-sitter-blade"
    [rust]="https://github.com/tree-sitter/tree-sitter-rust"
    [toml]="https://github.com/tree-sitter/tree-sitter-toml"
)
TS_CLI_MIN_VERSION="0.26.1"
PARSER_DIR="$HOME/.local/share/nvim/site/parser"

# Neovim supplies Markdown queries; external queries include inheritance dependencies.
TS_QUERY_LANGS=(bash html css yaml javascript typescript tsx vue json php php_only blade rust toml)
QUERY_DIR="$HOME/.local/share/nvim/site/queries"

build_parser() {
    local scanner
    for scanner in src/scanner.cc src/scanner.cpp; do
        if [ -f "$scanner" ]; then
            # Older grammars use C++ scanners, which the current CLI omits.
            require_commands c++ || return 1
            cc -fPIC -I src -c src/parser.c -o parser.o &&
                c++ -std=c++14 -fPIC -I src -c "$scanner" -o scanner.o &&
                c++ -shared -Wl,-z,defs parser.o scanner.o -o parser.so
            return $?
        fi
    done
    tree-sitter build
}

install_parsers() (
    shift # drop the leading --parsers
    require_commands git npm cc mktemp
    mkdir -p "$PARSER_DIR"

    if ! command -v tree-sitter >/dev/null 2>&1; then
        if ! command_exists pacman; then
            echo_error "tree-sitter-cli is required (at least $TS_CLI_MIN_VERSION). Install it with your package manager, then retry."
            return 1
        fi
        echo "tree-sitter-cli not found. Installing via pacman..."
        if [ "$(id -u)" -eq 0 ]; then
            pacman -S --needed tree-sitter-cli
        else
            require_commands sudo
            sudo pacman -S --needed tree-sitter-cli
        fi
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
    trap 'rm -rf -- "$tmp_dir"' EXIT

    local failures=0 lang
    for lang in "${langs[@]}"; do
        local spec="${TS_GRAMMARS[$lang]:-}"
        if [ -z "$spec" ]; then
            echo "Skipping '$lang': no known grammar repo configured in TS_GRAMMARS."
            failures=$((failures + 1))
            continue
        fi

        local repo_url="${spec%%#*}"
        local subdir=""
        [[ "$spec" == *#* ]] && subdir="${spec##*#}"

        echo "=== $lang ($repo_url${subdir:+ [$subdir]}) ==="
        local clone_dir="$tmp_dir/$lang"
        if ! clone_treesitter_source "$repo_url" "$clone_dir" "${TS_REVISIONS[$lang]}"; then
            echo "Failed to clone $repo_url, skipping $lang."
            failures=$((failures + 1))
            continue
        fi

        local build_dir="$clone_dir"
        [ -n "$subdir" ] && build_dir="$clone_dir/$subdir"

        if [ -f "$clone_dir/package.json" ]; then
            if ! (cd "$clone_dir" && npm install --ignore-scripts --no-audit --no-fund --silent); then
                echo "Failed to npm install for $lang, skipping."
                failures=$((failures + 1))
                continue
            fi
        fi

        if ! (cd "$build_dir" && tree-sitter generate && build_parser); then
            echo "Failed to build $lang, skipping."
            failures=$((failures + 1))
            continue
        fi

        local so_file
        so_file=$(find "$build_dir" -maxdepth 1 -iname "*.so" | head -1)
        if [ -z "$so_file" ]; then
            echo "No .so produced for $lang, skipping."
            failures=$((failures + 1))
            continue
        fi
        install_managed_file "$so_file" "$PARSER_DIR/$lang.so"
        echo "Installed $PARSER_DIR/$lang.so"
    done

    echo ""
    if [ "$failures" -gt 0 ]; then
        echo_error "$failures parser installation(s) failed. Successfully installed parsers were kept."
        return 1
    fi
    echo "Parser binaries installed to $PARSER_DIR (already on Neovim's native runtimepath)."
    echo "NOTE: this only builds the parser binaries. Highlight/indent query files"
    echo "(highlights.scm etc.) are a separate step, not something tree-sitter-cli produces."
)

install_queries() (
    shift # drop the leading --queries
    require_commands git mktemp cp
    mkdir -p "$QUERY_DIR"

    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap 'rm -rf -- "$tmp_dir"' EXIT

    echo "Cloning nvim-treesitter (master, archived/frozen) for its query files..."
    if ! clone_treesitter_source https://github.com/nvim-treesitter/nvim-treesitter "$tmp_dir/nvim-treesitter" "$TS_QUERY_REVISION"; then
        echo "Failed to clone nvim-treesitter, aborting."
        return 1
    fi

    local langs=("$@")
    if [ ${#langs[@]} -eq 0 ]; then
        langs=("${TS_QUERY_LANGS[@]}")
    fi

    if [[ " ${langs[*]} " == *" blade "* ]]; then
        clone_treesitter_source https://github.com/EmranMR/tree-sitter-blade "$tmp_dir/blade" "$TS_BLADE_REVISION" || return 1
        mkdir -p "$tmp_dir/nvim-treesitter/queries/blade"
        cp "$tmp_dir/blade/queries/"*.scm "$tmp_dir/nvim-treesitter/queries/blade/" || return 1
    fi
    local -A copied=()
    copy_query_language() {
        local language="$1" src="$tmp_dir/nvim-treesitter/queries/$1" dependency
        [[ "$language" =~ ^[a-z][a-z0-9_]*$ ]] || return 1
        [ "${copied[$language]:-}" = 1 ] && return 0
        if [ ! -d "$src" ]; then
            echo_error "Missing inherited query language: $language"
            return 1
        fi
        copied[$language]=1
        while IFS= read -r dependency; do
            [ -z "$dependency" ] || copy_query_language "$dependency" || return 1
        done < <(sed -n 's/^;[[:space:]]*inherits:[[:space:]]*//p' "$src/"*.scm | tr ',()' '\n' | tr -d ' ' | sort -u)
        mkdir -p "$QUERY_DIR/$language" || return 1
        local query_file
        for query_file in "$src/"*.scm; do
            install_managed_file "$query_file" "$QUERY_DIR/$language/$(basename "$query_file")" || return 1
        done
        echo "Installed queries for $language (including inherited dependencies)."
    }
    local failures=0 lang
    for lang in "${langs[@]}"; do
        if [[ ! "$lang" =~ ^[a-z][a-z0-9_]*$ ]]; then
            echo_error "Invalid query language: $lang"
            failures=$((failures + 1))
            continue
        fi
        if ! copy_query_language "$lang"; then
            failures=$((failures + 1))
        fi
    done

    echo ""
    if [ "$failures" -gt 0 ]; then
        echo_error "$failures query installation(s) failed."
        return 1
    fi
    echo "Query files installed to $QUERY_DIR (already on Neovim's native runtimepath)."
)

install_node_provider() (
    require_commands node npm
    node --version >/dev/null
    npm --version >/dev/null
    local prefix="$HOME/.local/share/nvim/node-provider"
    npm install --prefix "$prefix" --no-audit --no-fund --omit=dev neovim
    "$prefix/node_modules/.bin/neovim-node-host" --version
    echo "Node provider installed. Run :UpdateRemotePlugins in Neovim to register plugins."
)

usage() {
    cat <<EOF
Usage: $0 (--user|--global) [--force] [--legacy|--source]
       $0 --parsers [lang ...]
       $0 --queries [lang ...]
       $0 --node-provider

--force   Install even when an existing Neovim runs successfully.
--legacy  Use Neovim's unsupported, older-glibc build explicitly.
--source  Compile the stable release on this host (requires build tools).
A glibc failure offers legacy or source installation on an interactive terminal.
Non-interactive callers can retry with --legacy or --source.
Section installer equivalents: NVIM_LEGACY=1 or NVIM_SOURCE=1.
EOF
}

case "${1:-}" in
    --parsers) install_parsers "$@"; exit $? ;;
    --queries) install_queries "$@"; exit $? ;;
    --node-provider) install_node_provider; exit $? ;;
    --help|-h) usage; exit 0 ;;
esac

source "$DOTFILES_ROOT/scripts/install/neovim-aliases.sh"

INSTALL_TYPE=""
FORCE=0
LEGACY=0
SOURCE=0
for option in "$@"; do
    case "$option" in
        --user|--global)
            if [ -n "$INSTALL_TYPE" ]; then
                echo_error "Choose exactly one of --user and --global."
                exit 1
            fi
            INSTALL_TYPE=${option#--}
            ;;
        --force) FORCE=1 ;;
        --legacy) LEGACY=1 ;;
        --source) SOURCE=1 ;;
        *) echo_error "Unknown option: $option"; usage >&2; exit 1 ;;
    esac
done
if [ "$LEGACY" -eq 1 ] && [ "$SOURCE" -eq 1 ]; then
    echo_error "Choose either --legacy or --source, not both."
    exit 1
fi
if [ -z "$INSTALL_TYPE" ]; then
    usage >&2
    exit 1
fi
if [ "$INSTALL_TYPE" = global ] && [ "$(id -u)" -ne 0 ]; then
    echo_error "Global installation requires root privileges. Run with sudo."
    exit 1
fi

if command_exists nvim && [ "$FORCE" -eq 0 ]; then
    if version=$(nvim --version 2>&1) && startup=$(nvim --clean --headless +qa 2>&1); then
        echo "Neovim already works at $(command -v nvim): ${version%%$'\n'*}"
        install_neovim_aliases "$(command -v nvim)"
        echo "Use --force to install a new release."
        exit 0
    fi
    echo_error "The Neovim on PATH cannot run; attempting a replacement."
    printf '%s\n' "$version" "${startup:-}" >&2
fi

require_commands curl tar mktemp uname cp
case "$(uname -s)" in
    Linux) ;;
    *) echo_error "This binary installer supports Linux only."; exit 1 ;;
esac
case "$(uname -m)" in
    x86_64|amd64) architecture=x86_64 ;;
    aarch64|arm64) architecture=arm64 ;;
    *) echo_error "Unsupported CPU architecture: $(uname -m)"; exit 1 ;;
esac

TMP_DIR=$(mktemp -d)
new_install=""
cleanup() {
    rm -rf -- "$TMP_DIR"
    if [ -n "$new_install" ]; then
        rm -rf -- "$new_install"
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

archive="nvim-linux-$architecture"
resolve_release() {
    local repository="$1" latest_url
    latest_url=$(curl --fail --location --show-error --silent --output /dev/null \
        --write-out '%{url_effective}' "https://github.com/$repository/releases/latest") || return 1
    release_tag=${latest_url##*/}
    if [[ ! "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([.-][[:alnum:].-]+)?$ ]]; then
        echo_error "Could not resolve a stable Neovim release: $latest_url"
        return 1
    fi
}

fetch_release() {
    local repository="$1"
    resolve_release "$repository" || return 1
    echo "Downloading $repository $release_tag ($architecture)..."
    curl --fail --location --show-error --silent --output "$TMP_DIR/nvim.tar.gz" \
        "https://github.com/$repository/releases/download/$release_tag/$archive.tar.gz" || return 1
    rm -rf -- "$TMP_DIR/unpacked"
    mkdir -p "$TMP_DIR/unpacked"
    tar -xzf "$TMP_DIR/nvim.tar.gz" --no-same-owner -C "$TMP_DIR/unpacked" || return 1
    candidate="$TMP_DIR/unpacked/$archive/bin/nvim"
    if [ ! -x "$candidate" ]; then
        echo_error "The release archive does not contain an executable $archive/bin/nvim."
        return 1
    fi
}

if [ "$INSTALL_TYPE" = global ]; then
    prefix=/opt/neovim
    executable=/usr/local/bin/nvim
else
    prefix="$HOME/.local/opt/neovim"
    executable="$HOME/.local/bin/nvim"
fi
build_source() {
    require_commands git make cmake cc c++ || return 1
    if [[ ! "${NVIM_BUILD_JOBS:-2}" =~ ^[1-9][0-9]*$ ]]; then
        echo_error "NVIM_BUILD_JOBS must be a positive integer."
        return 1
    fi
    resolve_release neovim/neovim || return 1
    local source_dir="$TMP_DIR/source"
    mkdir -p "$source_dir" "$prefix" || return 1
    curl --fail --location --show-error --silent --output "$TMP_DIR/source.tar.gz" \
        "https://github.com/neovim/neovim/archive/refs/tags/$release_tag.tar.gz" || return 1
    tar -xzf "$TMP_DIR/source.tar.gz" --no-same-owner --strip-components=1 -C "$source_dir" || return 1
    new_install=$(mktemp -d "$prefix/$release_tag-source.XXXXXX") || return 1
    echo "Building Neovim $release_tag for this host (jobs: ${NVIM_BUILD_JOBS:-2})..."
    CMAKE_BUILD_PARALLEL_LEVEL="${NVIM_BUILD_JOBS:-2}" make -C "$source_dir" \
        CMAKE_BUILD_TYPE=Release CMAKE_INSTALL_PREFIX="$new_install" || return 1
    cmake --install "$source_dir/build" || return 1
    candidate="$new_install/bin/nvim"
}

verify_candidate() {
    version=$("$candidate" --version 2>&1) || return 1
    local startup
    if ! startup=$("$candidate" --clean --headless +qa 2>&1); then
        version="$version
$startup"
        return 1
    fi
}

build=supported
if [ "$SOURCE" -eq 1 ]; then
    build=source
    build_source
elif [ "$LEGACY" -eq 1 ]; then
    build=legacy
    echo_info "Using Neovim's unsupported legacy build (older glibc)."
    fetch_release neovim/neovim-releases
else
    fetch_release neovim/neovim
fi

while ! verify_candidate; do
    printf '%s\n' "$version" >&2
    if [ "$build" != source ] && [[ "$version" == *GLIBC_* ]]; then
        echo_error "This build requires a newer glibc than this host provides."
        echo "Options: 1) unsupported legacy build  2) build from source  3) cancel" >&2
        if [ -t 0 ]; then
            read -rp "Choose 1, 2, or 3 [3]: " answer || answer=3
        else
            answer=3
        fi
        case "$answer" in
            1|y|Y|yes)
                build=legacy
                fetch_release neovim/neovim-releases
                ;;
            2)
                build=source
                build_source
                ;;
            *)
                echo_error "Existing installation left untouched. Retry: $0 --$INSTALL_TYPE --legacy OR --source"
                exit 1
                ;;
        esac
    else
        echo_error "New Neovim cannot start. Existing installation left untouched."
        exit 1
    fi
done

if [ "$build" != source ]; then
    mkdir -p "$prefix"
    new_install=$(mktemp -d "$prefix/$release_tag-$build.XXXXXX")
    cp -a "$TMP_DIR/unpacked/$archive/." "$new_install/"
fi
# mktemp makes private directories; a global editor must be usable by other users.
chmod 755 "$new_install"
"$new_install/bin/nvim" --version >/dev/null
"$new_install/bin/nvim" --clean --headless +qa
backup_and_link "$executable" "$new_install/bin/nvim"
new_install=""

echo "Installed ${version%%$'\n'*} at $executable"
if [ "$INSTALL_TYPE" = user ]; then
    echo "Ensure $HOME/.local/bin is on PATH."
fi
install_neovim_aliases "$executable"
echo "Existing Neovim data and custom shell files were left intact."
