#!/usr/bin/env bash
(
    CHANNEL=nightly
	mkdir -p ~/.cache
	cd ~/.cache
	if [ -f ./nvim.appimage ]; then
        rm -f ./nvim.appimage
    fi

    curl -LO https://github.com/neovim/neovim/releases/download/$CHANNEL/nvim.appimage
    chmod u+x nvim.appimage

    rm -rf ~/squashfs-root ~/nvim
	./nvim.appimage --appimage-extract
	mv squashfs-root ~
    mv ~/squashfs-root ~/nvim

	source ~/.bashrc
)

rm -f ~/.cache/nvim.appimage
