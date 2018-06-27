"------Mappings----------

" Emmet-vim

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

vnoremap p "_dP                      “ dont overwrite register when pasting

"------Whitespace removal
highlight ExtraWhitespace ctermbg=red guibg=red
match ExtraWhitespace /\s\+$/

autocmd BufWinEnter * match ExtraWhitespace /\s\+$/
autocmd InsertEnter * match ExtraWhitespace /\s\+\%#\@<!$/
autocmd InsertLeave * match ExtraWhitespace /\s\+$/

autocmd BufWritePre *.php :%s/\s\+$//e


"-------Autocmd--------
autocmd BufEnter * if bufname("") !~ "^\[A-Za-z0-9\]*://" | lcd %:p:h | endif

autocmd  FileType  php set omnifunc=phpcomplete#CompletePHP
" let g:SuperTabDefaultCompletionType = "<Tab>"

let g:deoplete#enable_at_startup = 1


augroup autosourcing
    autocmd!
    autocmd BufWritePost .vimrc source %
augroup END

nnoremap <leader>m :silent make!\|redraw!\|vert cw<cr> 
nnoremap <leader>r :silent make run\|redraw!<cr>

