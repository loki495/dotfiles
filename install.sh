# Absolute path to this script. /home/user/bin/foo.sh
SCRIPT=$(readlink -f $0)
# Absolute path this script is in. /home/user/bin
SCRIPTPATH=`dirname $SCRIPT`

# BASH
mv ~/.bashrc ~/.bashrc.old
ln -s $SCRIPTPATH/bash/bashrc ~/.bashrc
echo "BASH done"

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
rm -rf ~/.vim/colors/
mkdir -p ~/bin
mkdir -p ~/.vim/plugged
mkdir -p ~/.vim/backup
mkdir -p ~/.vim/undo
mkdir -p ~/.vim/tmp
rm -f ~/bin/rg
rm -f ~/bin/vim-mappings
ln -s $SCRIPTPATH/dotfiles/bin/rg ~/bin/rg
ln -s $SCRIPTPATH/dotfiles/vim/vim-mappings ~/bin/vim-mappings
ln -s $SCRIPTPATH/vim/vimrc ~/.vimrc
ln -s $SCRIPTPATH/vim/colors ~/.vim/colors
touch ~/.vimrc.local
chmod 777 ~/bin/vim-mappings
chmod 777 ~/bin/rg

curl -sfLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null
vim +'PlugClean!' +'PlugInstall --sync' +qall

# YUM_CMD=$(which yum)
# APT_GET_CMD=$(which apt-get)

# if [[ ! -z $YUM_CMD ]]; then
#    sudo yum install fonts-powerline -y
#    sudo snap install ripgrep --classic
#    sudo snap alias ripgrep.rg rg
#elif [[ ! -z $APT_GET_CMD ]]; then
#    sudo apt-get install fonts-powerline -y
#    sudo snap install ripgrep --classic
#    sudo snap alias ripgrep.rg rg
#else
#    echo "error can't install package $PACKAGE"
#    exit 1;
#fi

echo "VIM done"

echo "DONE"
