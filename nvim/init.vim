set termguicolors

let mapleader = ','

let $NVIM_PYTHON_LOG_FILE="/tmp/nvim_log"
let $NVIM_PYTHON_LOG_LEVEL="DEBUG"

call plug#begin('~/.config/nvim/plugged')
so ~/dotfiles/nvim/plugins.vim
call plug#end()

so ~/dotfiles/nvim/plugins.settings.vim

" so ~/dotfiles/nvim/scratch.vim

so ~/dotfiles/nvim/general.vim

so ~/dotfiles/nvim/mappings.vim

