set termguicolors

nnoremap <SPACE> <Nop>
let mapleader = ','

let data_dir = '~/.config/nvim'
if empty(glob(data_dir . '/autoload/plug.vim'))
  silent execute '!curl -fLo '.data_dir.'/autoload/plug.vim --create-dirs  https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'
  autocmd VimEnter * PlugInstall --sync | source $MYVIMRC
endif

call plug#begin('~/.config/nvim/plugged')
so ~/dotfiles/nvim/plugins.vim
call plug#end()

so ~/dotfiles/nvim/coc.settings.vim
so ~/dotfiles/nvim/plugins.settings.vim

so ~/dotfiles/nvim/general.vim

so ~/dotfiles/nvim/mappings.vim

silent! source $HOME/.nvimrc.local

