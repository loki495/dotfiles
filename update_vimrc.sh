rm ~/.vimrc
rm ~/.vim/plugins.vim
ln -s `pwd`/vimrc ~/.vimrc
ln -s `pwd`/plugins.vim ~/.vim/
if cd  ~/.vim/bundle/Vundle.vim; then git pull; else git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim; fi
vim +PluginClean +PluginInstall +qall
