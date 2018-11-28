CURRENT_DIR=`pwd`
rm ~/.vimrc
rm ~/.vim/plugins.settings.vim
rm ~/.vim/general.vim
rm ~/.vim/mappings.vim
rm ~/.vim/plugins.vim
rm ~/.vim/colors/lucius.vim
rm -rf ~/.vim/plugins/
rm -rf ~/.vim/plugged/
mkdir ~/.vim/plugged
mkdir ~/.vim/backup
mkdir ~/.vim/undo
mkdir ~/.vim/tmp
mkdir ~/.vim/colors
ln -s `pwd`/vimrc ~/.vimrc
ln -s `pwd`/plugins.vim ~/.vim/
ln -s `pwd`/plugins.settings.vim ~/.vim/
ln -s `pwd`/general.vim ~/.vim/
ln -s `pwd`/mappings.vim ~/.vim/
ln -s `pwd`/lucius.vim ~/.vim/colors/
cd ~/.vim/plugged
git clone https://github.com/Shougo/vimproc.vim
cd ~/.vim/plugged/vimproc.vim
make
cd $CURRENT_DIR
curl -fLo ~/.vim/autoload/plug.vim --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
vim +PlugClean +PlugInstall +qall
