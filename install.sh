# Absolute path to this script. /home/user/bin/foo.sh
SCRIPT=$(readlink -f $0)
# Absolute path this script is in. /home/user/bin
SCRIPTPATH=`dirname $SCRIPT`

# BASH
mv ~/.bashrc ~/.bashrc.old
ln -s $SCRIPTPATH/bash/bashrc ~/.bashrc
source ~/.backrc
echo "BASH done"

mv ~/.dircolors ~/.dircolors.old
ln -s $SCRIPTPATH/bash/dircolors ~/.dircolors
echo "BASH done"

mv ~/.gitconfig ~/.gitconfig.old
ln -s $SCRIPTPATH/git/.gitconfig ~/.gitconfig
echo "GIT done"

# VIM
rm -f ~/.vimrc
rm -f ~/.vim/plugins.settings.vim
rm -f ~/.vim/general.vim
rm -f ~/.vim/mappings.vim
rm -f ~/.vim/plugins.vim
rm -f ~/.vim/colors/lucius.vim
rm -f ~/.vim/colors/scratch.vim
rm -rf ~/.vim/plugins/
rm -rf ~/.vim/plugged/
unlink ~/.vim/colors/ 2>/dev/null
mkdir -p ~/bin
mkdir -p ~/.vim/plugged
mkdir -p ~/.vim/backup
mkdir -p ~/.vim/undo
mkdir -p ~/.vim/tmp
ln -s $SCRIPTPATH/vim/vimrc ~/.vimrc
ln -s $SCRIPTPATH/vim/colors/ ~/.vim/colors
touch ~/.vimrc.local

curl -sfLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null

echo "VIM done"
echo "- run :PlugInstall"

mkdir -p ~/.config

# Garuda stuff
rm -rf ~/.config/wireplumber
ln -s $SCRIPTPATH/.config/wireplumber ~/.config/wireplumber
rm -rf ~/.config/waybar
ln -s $SCRIPTPATH/.config/waybar ~/.config/waybar
rm -rf ~/.config/hypr
ln -s $SCRIPTPATH/.config/hypr ~/.config/hypr
rm -rf ~/.config/fish
ln -s $SCRIPTPATH/.config/fish ~/.config/fish

# NVIM
rm -rf ~/.config/nvim
ln -s ~/dotfiles/nvim ~/.config/nvim

rm ~/.local/share/nvim/site/pack/packer -rf

~/dotfiles/install_neovim.sh

echo "NVIM done"

echo
echo "DONE"

