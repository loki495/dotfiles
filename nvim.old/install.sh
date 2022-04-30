# get latest nvim image
rm nvim.appimage* -f
curl -sL install-node.now.sh/lts | sudo bash -s -- -y
wget https://github.com/neovim/neovim/releases/latest/download/nvim.appimage
# set up nvim init.vim
echo 'source ~/dotfiles/nvim/init.vim' > ~/.config/nvim/init.vim

# install Plug for nvim
curl -sfLo ~/.config/nvim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null

#set up custom dirs
mkdir ~/.config/nvim/backup
mkdir ~/.config/nvim/undo
mkdir ~/.config/nvim/tmp
chmod a+x ./nvim.appimage

#extract nvim (for shared hosts)
./nvim.appimage --appimage-extract

# set up bashrc alias
sed '/nvim/d' ~/.bashrc > ~/.bashrc
echo 'alias nvim="$HOME/dotfiles/nvim/squashfs-root/usr/bin/nvim -u /home/ubuntu/dotfiles/nvim/init.vim"' >> ~/.bashrc
source ~/.bashrc

# install plugins
nvim +PlugClean +'PlugInstall --sync' +'CocInstall coc-phpls' +qall
