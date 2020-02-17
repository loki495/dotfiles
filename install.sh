CURRENT_DIR=`pwd`
rm -f ~/.vimrc
rm -f ~/.vim/plugins.settings.vim
rm -f ~/.vim/general.vim
rm -f ~/.vim/mappings.vim
rm -f ~/.vim/plugins.vim
rm -f ~/.vim/colors/lucius.vim
rm -f ~/.vim/colors/scratch.vim
rm -rf ~/.vim/plugins/
rm -rf ~/.vim/plugged/
rm -rf ~/.vim/colors/*.vim
mkdir -p ~/bin
mkdir -p ~/.vim/plugged
mkdir -p ~/.vim/backup
mkdir -p ~/.vim/undo
mkdir -p ~/.vim/tmp
mkdir -p ~/.vim/colors
ln -s `pwd`/rg ~/bin/rg
ln -s `pwd`/vimrc ~/.vimrc
cp --symbolic-link `pwd`/colors/*.vim ~/.vim/colors
touch ~/.vimrc.local

cd $CURRENT_DIR
curl -sfLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null
vim +PlugClean +'PlugInstall --sync' +qall

YUM_CMD=$(which yum)
APT_GET_CMD=$(which apt-get)

if [[ ! -z $YUM_CMD ]]; then
    sudo yum install fonts-powerline -y
    sudo snap install ripgrep --classic
    sudo snap alias ripgrep.rg rg
elif [[ ! -z $APT_GET_CMD ]]; then
    sudo apt-get install fonts-powerline -y
    sudo snap install ripgrep --classic
    sudo snap alias ripgrep.rg rg
else
    echo "error can't install package $PACKAGE"
    exit 1;
fi
echo "DONE setting up vim..."
