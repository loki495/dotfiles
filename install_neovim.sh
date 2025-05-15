#!/usr/bin/env bash
(
    cd ~

    rm -rf nvim-linux64.tar.gz
    rm -rf ~/nvim-linux64/
    rm -rf ~/nvim/
    wget "https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz"
    tar xvf nvim-linux-x86_64.tar.gz
    mv ~/nvim-linux-x86_64/ ~/nvim
    rm -rf nvim-linux-x86_64.tar.gz
)
