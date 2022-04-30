" General
scriptencoding utf-8

set noautochdir

set scl=no

set tags+=tags,tags.vendor,/
" set autowriteall
set backspace=indent,eol,start
set completeopt=longest,menuone
set complete=.,i,t,b,u
set cpoptions-=$                " cool trick to show what you're replacing
set encoding=utf-8
set virtualedit=                " allow for cursor beyond last character
set history=1000                " Store a ton of history (default is 20)

set mouse-=a                    " automatically disable mouse usage

" Undo/Tmp/Backup
set undofile
set backup
set backupdir=~/.config/nvim/backup
set directory=~/.config/nvim/tmp
set undodir=~/.config/nvim/undo

" formatroptions
set formatoptions-=r            " no auto-comment with Enter
set formatoptions-=o            " don't auto-comment with o or O
set formatoptions-=t            " don't auto-wrap non-commented text
silent! set formatoptions+=j    " let J handle comments if supported

" Search
set ignorecase                  " case insensitive search
set incsearch                   " find as you type search
set smartcase                   " case sensitive when uc present

" Splits
set splitbelow
set splitright

" Tabs / Spaces
set autoindent                  " indent at the same level of the previous line
set expandtab                   " tabs are spaces, not tabs
set shiftwidth=4                " use indents of 4 spaces
set softtabstop=4               " let backspace delete indent
set tabstop=4                   " an indentation every four columns
set smarttab



"--------Visuals---------

syntax on                       " syntax highlighting

set guifont=Ubuntu\ Mono\ derivative\ Powerline         " Way better than monospace
set winminheight=0              " windows can be 0 line high
set hlsearch                    " highlight search terms
set number                      " line numbers on
set numberwidth=5
set cursorline
set colorcolumn=
set scrolloff=3                 " minimum lines to keep above and below cursor
set shortmess+=I                " Disable splash text
set laststatus=2                " Always show status bar
set linespace=15                " no extra spaces between rows
set scrolljump=5                " lines to scroll when cursor leaves screen
set showmatch                   " show matching brackets/parenthesis
set pumheight=10                " so the complete menu doesn't get too big

set wildmenu                    " show list instead of just completing
set wildmode=list:longest       " ,full " command <Tab> completion, list matches, then longest common part, then all.

colorscheme gruvbox
