rm ~/.vimrc
rm ~/.vim/plugins.vim
rm ~/.vim/colors/lucius.vim
ln -s `pwd`/vimrc ~/.vimrc
ln -s `pwd`/plugins.vim ~/.vim/
ln -s `pwd`/lucius.vim ~/.vim/colors/
if cd  ~/.vim/bundle/Vundle.vim; then git pull; else git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim; fi
vim +PluginClean +PluginInstall +qall
