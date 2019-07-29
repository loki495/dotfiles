" se

set termguicolors

let mapleader = ','

let $NVIM_PYTHON_LOG_FILE="/tmp/nvim_log"
let $NVIM_PYTHON_LOG_LEVEL="DEBUG"

let g:plug_threads = 1
let g:ale_completion_enabled = 1
let g:ale_fixers = {
\   '*': ['remove_trailing_lines', 'trim_whitespace'],
\   'javascript': ['eslint'],
\}
let g:ale_fix_on_save = 1

call plug#begin('~/.vim/plugged')
so ~/.vim/plugins.vim
call plug#end()

so ~/.vim/general.vim

so ~/.vim/mappings.vim

so ~/.vim/plugins.settings.vim

" Local sourcing.
if filereadable($HOME."/.vimrc.local")
  source $HOME/.vimrc.local
endif
