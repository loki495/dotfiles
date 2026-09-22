# shellcheck shell=bash

install_neovim_aliases() (
    set -e
    local executable="$1" directory="$HOME/.local/share/dotfiles" temporary quoted fish_quoted
    mkdir -p "$directory"
    temporary=$(mktemp -d "$directory/.aliases.XXXXXX")
    trap 'rm -rf -- "$temporary"' EXIT
    # Quote twice: once for the alias command and once for its expansion.
    printf -v quoted '%q' "$executable"
    {
        printf '# Managed by the dotfiles Neovim installer.\n'
        printf 'alias nvim=%q\nalias vim=%q\n' "$quoted" "$quoted"
    } > "$temporary/neovim.bash"
    fish_quoted=${executable//\\/\\\\}
    fish_quoted=${fish_quoted//\'/\\\'}
    {
        printf '# Managed by the dotfiles Neovim installer.\n'
        printf "function nvim\n    command '%s' \$argv\nend\n" "$fish_quoted"
        printf "function vim\n    command '%s' \$argv\nend\n" "$fish_quoted"
    } > "$temporary/neovim.fish"
    install_managed_file "$temporary/neovim.bash" "$directory/neovim.bash"
    install_managed_file "$temporary/neovim.fish" "$directory/neovim.fish"
    echo "Neovim shell aliases written to $directory/neovim.{bash,fish}."
    echo "Open a new shell, or source the matching file in your current shell."
)
