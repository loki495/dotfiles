#!/usr/bin/env bash
(
    cd ~

    rm -rf nvim-linux64.tar.gz
    rm -rf ~/nvim-linux64/
    rm -rf ~/nvim/
    if [ "$1" = "old" ]; then
        echo "Older GLibC installing..."
        wget "https://github.com/neovim/neovim-releases/releases/download/nightly/nvim-linux-x86_64.tar.gz"
    else
        echo "Newer GLibC installing..."
        wget "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz"
    fi
    tar xvf nvim-linux-x86_64.tar.gz
    mv ~/nvim-linux-x86_64/ ~/nvim
    rm -rf nvim-linux-x86_64.tar.gz
)
