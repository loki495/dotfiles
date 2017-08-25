set nocompatible                   " Use ViMproved, don't emulate old vi
let $VIMHOME = split(&rtp, ',')[0] " Find the Vim path

filetype off " Turned back on after loading bundles
set rtp+=$VIMHOME/bundle/Vundle.vim
call vundle#begin()
Plugin 'VundleVim/Vundle.vim',

filetype plugin indent on " Automatically detect file types.
syntax on                 " syntax highlighting
set mouse-=a               " automatically disable mouse usage
set virtualedit=all       " allow for cursor beyond last character
set history=1000          " Store a ton of history (default is 20)
set hidden                " allow buffer switching without saving
scriptencoding utf-8
set encoding=utf-8
autocmd BufEnter * if bufname("") !~ "^\[A-Za-z0-9\]*://" | lcd %:p:h | endif
" autocmd VimEnter * execute "cd" fnameescape(g:startDir)

set backspace=indent,eol,start " backspace for dummies
set linespace=0                " no extra spaces between rows
set number                     " line numbers on
set cpoptions-=$               " cool trick to show what you're replacing
set showmatch                  " show matching brackets/parenthesis
" set showcmd                    " show multi-key commands as you type
set incsearch                  " find as you type search
set nohlsearch                   " highlight search terms
set winminheight=0             " windows can be 0 line high
set ignorecase                 " case insensitive search
set smartcase                  " case sensitive when uc present
set wildmenu                   " show list instead of just completing
set wildmode=list:longest " ,full " command <Tab> completion, list matches, then longest common part, then all.
set scrolljump=5               " lines to scroll when cursor leaves screen
set scrolloff=3                " minimum lines to keep above and below cursor
" set list                       " use the listchars settings
" set listchars=tab:▸\           " show tabs
set colorcolumn=81
"color is for lucius dark
hi ColorColumn guibg=#292929

set shortmess+=I                       " Disable splash text
set t_Co=256                           " Fix colors in the terminal
set guifont=Ubuntu\ Mono\ derivative\ Powerline         " Way better than monospace
color lucius                    " Vim colorscheme
LuciusDark
set cursorline


let g:Powerline_colorscheme = 'murmur' " Powerline colorscheme
set laststatus=2                       " Always show status bar
" let mousemodel-=popup                   " Enable context menu

"set nowrap        " wrap long lines
set autoindent    " indent at the same level of the previous line
set shiftwidth=4  " use indents of 4 spaces
set expandtab     " tabs are spaces, not tabs
set tabstop=4     " an indentation every four columns
set softtabstop=4 " let backspace delete indent
" Remove trailing whitespaces and ^M chars
" autocmd FileType c,cpp,java,php,javascript,python,twig,xml,yml,phtml,vimrc autocmd BufWritePre <buffer> :call setline(1,map(getline(1,"$"),'substitute(v:val,"\\s\\+$","","")'))

" set statusline+=%{gutentags#statusline()}

map  <F1> <Esc>
imap <F1> <Esc>

Plugin 'yuttie/comfortable-motion.vim'
Plugin 'vim-scripts/taglist.vim'
" Plugin 'ludovicchabant/vim-gutentags'
Plugin 'hattya/vcvars.vim'
Plugin 'will133/vim-dirdiff'
Plugin 'ervandew/supertab'
" Plugin 'lifepillar/vim-mucomplete'
Plugin 'vim-airline/vim-airline'
Plugin 'vim-airline/vim-airline-themes'
Plugin 'spf13/vim-colors'
Plugin 'airblade/vim-gitgutter'
Plugin 'powerline/powerline'
Plugin 'mattn/emmet-vim'
Plugin 'scrooloose/syntastic', '3.0.0'
Plugin 'joonty/vdebug'
" Plugin 'StanAngeloff/php.vim'
" Plugin 'shawncplus/phpcomplete.vim'
" Plugin 'EvanDotPro/php_getset.vim'
Plugin 'mikehaertl/pdv-standalone'
Plugin 'SirVer/ultisnips'
Plugin 'honza/vim-snippets'
" Plugin 'shougo/neocomplete.vim'
" Plugin 'mbbill/code_complete'
Plugin 'Shougo/vimproc', {
      \ 'build' : {
      \     'windows' : 'make -f make_mingw32.mak',
      \     'cygwin' : 'make -f make_cygwin.mak',
      \     'mac' : 'make -f make_mac.mak',
      \     'unix' : 'make -f make_unix.mak',
      \    },
     \ }
Plugin 'Shougo/unite.vim'
Plugin 'm2mdas/phpcomplete-extended'

autocmd  FileType  php setlocal omnifunc=phpcomplete_extended#CompletePHP
" autocmd FileType php setlocal omnifunc=phpcomplete#CompletePHP
let g:phpcomplete_index_composer_command = 'composer'

" set completeopt=longest,menuone


map <C-B> :FufBuffer<CR>
cmap w!! w !sudo tee % >/dev/null


"function! InitializeDirectories()
"    let parent = $VIMHOME
"    let prefix = '.'
"    let dir_list = {
"                \ 'backup': 'backupdir',
"                \ 'views': 'viewdir',
"                \ 'swap': 'directory' }
"
"    if has('persistent_undo')
"        let dir_list['undo'] = 'undodir'
"    endif
"
"    for [dirname, settingname] in items(dir_list)
"        let directory = parent . '/' . prefix . dirname . '/'
"        if exists('*mkdir')
"            if !isdirectory(directory)
"                call mkdir(directory)
"            endif
"        endif
"        if !isdirectory(directory)
"            echo 'Warning: Unable to create backup directory: ' . directory
"            echo 'Try: mkdir -p ' . directory
"        else
"            let directory = substitute(directory, " ", "\\\\ ", 'g')
"            " add trailing slashes to name swap files with full path
"            exec 'set ' . settingname . '^=' . directory . '//'
"        endif
"    endfor
"endfunction
"
"call InitializeDirectories()


call vundle#end()
filetype plugin indent on

" air-line
let g:airline_theme='murmur'
let g:airline_powerline_fonts = 1
let g:Powerline_symbols='unicode'

if !exists('g:airline_symbols')
    let g:airline_symbols = {}
endif

" unicode symbols
let g:airline_left_sep = ''
let g:airline_left_sep = ''
let g:airline_right_sep = ''
let g:airline_right_sep = ''
let g:airline_symbols.linenr = ''
let g:airline_symbols.linenr = ''
let g:airline_symbols.linenr = ''
let g:airline_symbols.branch = ''
let g:airline_symbols.paste = 'ρ'
let g:airline_symbols.paste = 'Þ'
let g:airline_symbols.paste = ''
let g:airline_symbols.whitespace = 'Ξ'

" airline symbols
let g:airline_left_sep = ''
let g:airline_left_alt_sep = ''
let g:airline_right_sep = ''
let g:airline_right_alt_sep = ''
let g:airline_symbols.branch = ''
let g:airline_symbols.readonly = ''
let g:airline_symbols.linenr = ''


map <C-t> :Ex<Cr>
unmap! <C-e>
imap <C-e> <Esc>e<Space>i
" set runtimepath^=~/.vim/bundle/ctrlp.vim
" let g:ctrlp_map = '<c-p>' 
" let g:ctrlp_cmd = 'CtrlPBuffer'
" let g:ctrlp_open_new_file = 't'

" autocmd FileType php setlocal omnifunc=phpcomplete#CompletePHP

" set completeopt=longest,menuone

let g:SuperTabDefaultCompletionType = "<c-x><c-o>"

let g:mucomplete#enable_auto_at_startup = 1

" Trigger configuration. Do not use <tab> if you use https://github.com/Valloric/YouCompleteMe.
let g:UltiSnipsExpandTrigger="<c-j>"
let g:UltiSnipsJumpForwardTrigger="<c-b>"
let g:UltiSnipsJumpBackwardTrigger="<c-z>"

" If you want :UltiSnipsEdit to split your window.
" let g:UltiSnipsEditSplit="vertical"

set pumheight=10             " so the complete menu doesn't get too big
" set completeopt=menu,longest " menu, menuone, longest and preview
let g:SuperTabDefaultCompletionType='context'

let g:netrw_use_errorwindow=0   " suppress error window
let g:netrw_liststyle=3         " thin
let g:netrw_altv=1
let g:netrw_browse_split = 3

iabbrev cdata <![CDATA[]]>
iabbrev echol echo '<pre>'.__LINE__.' - '.__FILE__."\n";$e = new \Exception();print_r($e->getTraceAsString());print_r();exit;<Esc><S-f>)i

" set backspace=2 " make backspace work like most other apps
set backspace=indent,eol,start

set directory=~/.vim/tmp
set backup
set backupdir=~/.vim/backup
set undofile
set undodir=~/.vim/undo
set formatoptions-=t            " don't auto-wrap non-commented text
set formatoptions-=o            " don't auto-comment with o or O
set formatoptions+=r            " auto-comment with Enter
silent! set formatoptions+=j    " let J handle comments if supported

let Tlist_Use_Right_Window=1
let Tlist_Auto_Open=0
let Tlist_Enable_Fold_Column=0
let Tlist_Compact_Format=0
let Tlist_WinWidth=28
let Tlist_Exit_OnlyWindow=1
let Tlist_File_Fold_Auto_Close = 1
nmap <LocalLeader>tt :Tlist<cr>

" Tab navigation like Firefox.
nnoremap <C-S-tab> :tabprevious<CR>
nnoremap <C-tab>   :tabnext<CR>
nnoremap <C-t>     :tabnew<CR>
inoremap <C-S-tab> <Esc>:tabprevious<CR>i
inoremap <C-tab>   <Esc>:tabnext<CR>i
inoremap <C-t>     <Esc>:tabnew<CR>

