CURRENT_DIR=`pwd`
rm -f ~/.vimrc
rm -f ~/.vim/plugins.settings.vim
rm -f ~/.vim/general.vim
rm -f ~/.vim/mappings.vim
rm -f ~/.vim/plugins.vim
rm -f ~/.vim/colors/lucius.vim
rm -rf ~/.vim/plugins/
rm -rf ~/.vim/plugged/
mkdir -p ~/bin
mkdir -p ~/.vim/plugged
mkdir -p ~/.vim/backup
mkdir -p ~/.vim/undo
mkdir -p ~/.vim/tmp
mkdir -p ~/.vim/colors
ln -s `pwd`/rg ~/bin/rg
ln -s `pwd`/vimrc ~/.vimrc
ln -s `pwd`/plugins.vim ~/.vim/
ln -s `pwd`/plugins.settings.vim ~/.vim/
ln -s `pwd`/general.vim ~/.vim/
ln -s `pwd`/mappings.vim ~/.vim/
ln -s `pwd`/lucius.vim ~/.vim/colors/
ln -s `pwd`/paragold-ora.vim ~/.vim/colors/
ln -s `pwd`/paragold.vim ~/.vim/colors/
cd $CURRENT_DIR
curl -sfLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim > /dev/null
vim +PlugClean +'PlugInstall --sync' +qall

if [[ ! -z $YUM_CMD ]]; then
    sudo yum install fonts-powerline
elif [[ ! -z $APT_GET_CMD ]]; then
    sudo apt-get install fonts-powerline
else
    echo "error can't install package $PACKAGE"
    exit 1;
fi
echo "DONE setting up vim..."
