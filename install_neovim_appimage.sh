#!/usr/bin/env bash
(
    cd ~

    rm -rf nvim-linux64.tar.gz
    rm -rf ~/nvim-linux64/
    wget "https://github.com/neovim/neovim/releases/latest/download/nvim-linux64.tar.gz"
    tar xvf nvim-linux64.tar.gz
    mv ~/nvim-linux64/ ~/nvim
    rm -rf nvim-linux64.tar.gz
)
