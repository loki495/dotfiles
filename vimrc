set nocompatible                        " Use ViMproved, don't emulate old vi


let mapleader = ','

let $VIMHOME = split(&rtp, ',')[0]      " Find the Vim path
set rtp+=$VIMHOME/bundle/Vundle.vim
call vundle#begin()

so ~/.vim/plugins.vim

call vundle#end()
filetype plugin indent on


"---------Options--------

" General
scriptencoding utf-8

set tags+=tags,tags.vendor
set autowriteall
set backspace=indent,eol,start
set completeopt=menu,longest    " menu, menuone, longest and preview
set complete=.,i,t,b,u
set cpoptions-=$                " cool trick to show what you're replacing
set encoding=utf-8
set virtualedit=                " allow for cursor beyond last character
set history=1000                " Store a ton of history (default is 20)

set mouse-=a                    " automatically disable mouse usage

" Undo/Tmp/Backup
set undofile
set backup
set backupdir=~/.vim/backup
set directory=~/.vim/tmp
set undodir=~/.vim/undo

" formaroptions
set formatoptions+=r            " auto-comment with Enter
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



"--------Visuals---------

set t_Co=256                           " Fix colors in the terminal
syntax on                       " syntax highlighting

hi ColorColumn guibg=#292929
set guifont=Ubuntu\ Mono\ derivative\ Powerline         " Way better than monospace
color lucius                    " Vim colorscheme
LuciusDark

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

"-------Plugins----------

" airline
let g:airline_theme='murmur'
let g:airline_powerline_fonts = 1
let g:Powerline_symbols='unicode'

let g:html_indent_tags = 'li\|p'

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

"/
"/ Ag
"/
let g:ackprg = 'ag --nogroup --nocolor --column'

"/
"/ PhpInsertUse
"/
function! IPhpInsertUse()
    call PhpInsertUse()
    call feedkeys('a',  'n')
endfunction

autocmd FileType php inoremap <Leader>n <Esc>:call IPhpInsertUse()<CR>
autocmd FileType php noremap <Leader>n :call PhpInsertUse()<CR>
"/
"/ Powerline
"/
let g:Powerline_colorscheme = 'murmur' " Powerline colorscheme

"/
"/ phpcomplete
"/
let g:phpcomplete_index_composer_command = 'composer'

"/
"/ CtlP
"/
" let g:ctrlp_map = '<c-p>' 
" let g:ctrlp_cmd = 'CtrlPBuffer'
" let g:ctrlp_open_new_file = 't'
" let g:ctrlp_custom_ignore = {
"   \ 'dir':  '\v[\/]\.(git|hg|svn)$',
"   \ 'vendor':  '\vendor$',
"   \ 'file': '\v\.(exe|so|dll)$',
"   \ }
" let g:ctrlp_match_window = 'top,order:ttb,min:1,max:30,results:30'
" let g:ctrlp_user_command = 'find . -type f ! -path *.git* ! -path *.jpg ! -path *.gif ! -path *.png ! -path *.bmp'
" map <C-p> :CtrlP<Cr>
" map <C-t> :CtrlPBufTag<Cr>

"/
"/ FZF
"/
nmap ; :Buffers<CR>
nmap <Leader>t :Files<CR>
nmap <Leader>r :Tags<CR>



"/
"/ Supertab
"/
let g:SuperTabDefaultCompletionType = "<c-x><c-o>"
let g:SuperTabDefaultCompletionType='context'

"/
"/ Mucomplete
"/
" let g:mucomplete#enable_auto_at_startup = 1

"/
"/ Ultisnips
"/
let g:UltiSnipsExpandTrigger="<tab>"
let g:UltiSnipsJumpForwardTrigger="<tab>"
let g:UltiSnipsJumpBackwardTrigger="<tab>"

"/
"/ NERDTree
"/
nmap <Leader>1 :NERDTreeToggle<cr>
let NERDTreeHijackNetrw = 0

"/
"/ Netrw
"/
let g:netrw_use_errorwindow=0   " suppress error window
let g:netrw_liststyle=3         " thin
let g:netrw_altv=1
let g:netrw_browse_split = 3

"/
"/ Tlist
"/
let Tlist_Use_Right_Window=1
let Tlist_Auto_Open=0
let Tlist_Enable_Fold_Column=0
let Tlist_Compact_Format=0
let Tlist_WinWidth=28
let Tlist_Exit_OnlyWindow=1
let Tlist_File_Fold_Auto_Close = 1


"------Mappings----------

" map <C-B> :FufBuffer<CR>
cmap w!! w !sudo tee % >/dev/null

" Switch between the last two files
nnoremap <Leader><Leader> <C-^>

" Get off my lawn
nnoremap <Left> :echoe "Use h"<CR>
nnoremap <Right> :echoe "Use l"<CR>
nnoremap <Up> :echoe "Use k"<CR>
nnoremap <Down> :echoe "Use j"<CR>


nmap <Leader>b :bu <C-I>
nmap <Leader><Tab> :bn<cr>
nmap <Leader><S-Tab> :bp<cr>
" unmap! <C-e>
imap <C-e> <Esc>e<Space>i
imap <C-r> <C-o>b

iabbrev cdata <![CDATA[]]>
iabbrev echol echo '<pre>'.__LINE__.' - '.__FILE__."\n";$e = new \Exception();print_r($e->getTraceAsString());print_r();exit;<Esc><S-f>)i
iabbrev coutl cout << __LINE__ << " - " << __FILE__ << endl <<x<< endl;<Esc><S-f>xxi

nmap <Leader><space> :nohlsearch<cr>
nmap <Leader>ev :tabnew $MYVIMRC<cr>
nmap <Leader>ep :tabnew ~/.vim/plugins.vim<cr>

nmap <LocalLeader>tt :Tlist<cr>

" simpler split navigation
nmap <C-H> <C-W><C-H>
nmap <C-J> <C-W><C-J>
" nmap <C-K> <C-W><C-K>
nmap <C-L> <C-W><C-L>

map <F4> :e %:p:s,.h$,.X123X,:s,.cpp$,.h,:s,.X123X$,.cpp,<CR>

"------Whitespace removal
highlight ExtraWhitespace ctermbg=red guibg=red
match ExtraWhitespace /\s\+$/

autocmd BufWinEnter * match ExtraWhitespace /\s\+$/
autocmd InsertEnter * match ExtraWhitespace /\s\+\%#\@<!$/
autocmd InsertLeave * match ExtraWhitespace /\s\+$/

autocmd BufWritePre *.php :%s/\s\+$//e


"-------Autocmd--------
autocmd BufEnter * if bufname("") !~ "^\[A-Za-z0-9\]*://" | lcd %:p:h | endif
autocmd  FileType  php setlocal omnifunc=phpcomplete_extended#CompletePHP

augroup autosourcing
    autocmd!
    autocmd BufWritePost .vimrc source %
augroup END

