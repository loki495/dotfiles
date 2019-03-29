"------Mappings----------

" Emmet-vim

" map <C-B> :FufBuffer<CR>
cmap w!! w !sudo tee % >/dev/null

" Switch between the last two files
" nnoremap <Leader><Leader> <C-^>

" Get off my lawn
nnoremap <Left> :echoe "Use h"<CR>
nnoremap <Right> :echoe "Use l"<CR>
nnoremap <Up> :echoe "Use k"<CR>
nnoremap <Down> :echoe "Use j"<CR>

imap <C-e> <Esc>e<Space>i

iabbrev cdatal <![CDATA[]]><Left><Left><Left>
iabbrev echol echo '<pre>'.__LINE__.' - '.__FILE__."\n";$e = new \Exception();print_r($e->getTraceAsString());print_r();exit;<Esc><S-f>)i
iabbrev coutl cout << __LINE__ << " - " << __FILE__ << endl <<x<< endl;<Esc><S-f>xxi

nmap <Leader><space> :nohlsearch<cr>
nmap <Leader>ev :tabnew $MYVIMRC<cr>
nmap <Leader>ep :tabnew ~/.vim/plugins.vim<cr>


" simpler split navigation
nmap <C-H> <C-W><C-H>
nmap <C-J> <C-W><C-J>
nmap <C-K> <C-W><C-K>
nmap <C-L> <C-W><C-L>

map <F4> :e %:p:s,.h$,.X123X,:s,.cpp$,.h,:s,.X123X$,.cpp,<CR>

vnoremap p "_dP                      “ dont overwrite register when pasting

nnoremap <Leader>] gt
nnoremap <Leader>[ gT

"------Whitespace removal
highlight ExtraWhitespace ctermbg=red guibg=red
" match ExtraWhitespace /\s\+$/

autocmd BufWinEnter * match ExtraWhitespace /\s\+$/
autocmd InsertEnter * match ExtraWhitespace /\s\+\%#\@<!$/
autocmd InsertLeave * match ExtraWhitespace /\s\+$/

autocmd BufWritePre *.php :%s/\s+$//e


"-------Autocmd--------
" autocmd BufEnter * if bufname("") !~ "^\[A-Za-z0-9\]*://" | lcd %:p:h | endif

augroup autosourcing
    autocmd!
    autocmd BufWritePost .vimrc source %
    autocmd BufWritePost *.vim source %
augroup END

nnoremap <leader>m :silent make!\|redraw!\|vert cw<cr>
nnoremap <leader>r :silent make run\|redraw!<cr>

"------ Functions ------
function! SearchFromCursor()
  let curline = getline('.')
  call inputsave()
  let search = input('Search pattern: ')
  call inputrestore()

  call inputsave()
  let replace = input('Replace with: ')
  call inputrestore()

  let str = ',$s~' . search . '~' . replace . '~gc'
  redraw
  execute str
endfunction

inoremap <Leader>A <C-o>:call SearchFromCursor()<cr>
noremap <Leader>A <C-o>:call SearchFromCursor()<cr>

noremap <C-a> :"ad<CR>
"------Mappings----------

cmap w!! w !sudo tee % >/dev/null

nnoremap <Leader>] gt
nnoremap <Leader>[ gT

" Run file as PHP
inoremap <Leader>p :!php %<cr>
noremap <Leader>p :!php %<cr>

"/ CTRL_Backspace delete from cursor to beginning of word
inoremap  <Esc><Right>dbi

" Jump to matching delimiters more easily.
nnoremap <leader><Tab> %
noremap <leader><Tab> %

inoremap <C-k> <C-o>k
inoremap <C-j> <C-o>j
inoremap <C-h> <C-o>h
inoremap <C-l> <C-o>l
