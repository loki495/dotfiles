" se


let mapleader = ','

let $NVIM_PYTHON_LOG_FILE="/tmp/nvim_log"
let $NVIM_PYTHON_LOG_LEVEL="DEBUG"

let g:plug_threads = 1

call plug#begin('~/.vim/plugged')
so ~/.vim/plugins.vim
call plug#end()

" filetype plugin indent on

so ~/.vim/plugins.settings.vim

so ~/.vim/general.vim

so ~/.vim/mappings.vim
