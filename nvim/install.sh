rm nvim.appimage* -f
curl -sL install-node.now.sh/lts | sudo bash -s -- -y
wget https://github.com/neovim/neovim/releases/download/nightly/nvim.appimage
curl -sfLo ~/.config/nvim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null
mkdir ~/.config/nvim/backup
mkdir ~/.config/nvim/undo
mkdir ~/.config/nvim/tmp
chmod a+x ./nvim.appimage
./nvim.appimage --appimage-extract
sed '/nvim/d' ~/.bashrc > ~/.bashrc
echo 'alias nvim="/home/ec2-user/dotfiles/nvim/squashfs-root/usr/bin/nvim -u /home/ec2-user/dotfiles/nvim/init.vim"' >> ~/.bashrc
source ~/.bashrc
echo 'source ~/dotfiles/nvim/init.vim' > ~/.config/nvim/init.vim
/home/ec2-user/dotfiles/nvim/squashfs-root/usr/bin/nvim +PlugClean +'PlugInstall --sync' +'CocInstall coc-phpls' +qall
