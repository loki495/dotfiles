" se

if &term =~# '256color' && ( &term =~# '^screen'  || &term =~# '^tmux' )
    let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
    let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
    set termguicolors
endif

let mapleader = ','

let g:plug_threads = 1
let g:ale_completion_enabled = 1
let g:ale_fixers = {
\   '*': ['remove_trailing_lines', 'trim_whitespace'],
\   'javascript': ['eslint'],
\}
let g:ale_fix_on_save = 1

call plug#begin('~/.vim/plugged')
so ~/dotfiles/plugins.vim
call plug#end()

so ~/dotfiles/mappings.vim

so ~/dotfiles/plugins.settings.vim

so ~/dotfiles/general.vim

source $HOME/.vimrc.local
