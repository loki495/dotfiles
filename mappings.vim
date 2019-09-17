"------Mappings----------

" Emmet-vim

" map <C-B> :FufBuffer<CR>

set foldmethod=indent
" set foldnestmax=10
" set nofoldenable
set foldlevel=2

hi Folded guibg=#000000 guifg=#505050

cmap w!! w !sudo tee % >/dev/null

" Switch between the last two files
" nnoremap <Leader><Leader> <C-^>

" Get off my lawn
nnoremap <Left> :echoe "Use h"<CR>
nnoremap <Right> :echoe "Use l"<CR>
nnoremap <Up> :echoe "Use k"<CR>
nnoremap <Down> :echoe "Use j"<CR>

nnoremap <Leader>o R<cr><esc>d0

imap <C-e> <Esc>e<Space>i

iabbrev cdatal <![CDATA[]]><Left><Left><Left>
iabbrev echol echo '<pre>'.__LINE__.' - '.__FILE__."\n";$e = new \Exception();print_r($e->getTraceAsString());echo"\n";print_r();exit;<Esc><S-f>)i
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

" Restore cursor position, window position, and last search after running a
" command.
function! Preserve(command)
  " Save the last search.
  let search = @/

  " Save the current cursor position.
  let cursor_position = getpos('.')

  " Save the current window position.
  normal! H
  let window_position = getpos('.')
  call setpos('.', cursor_position)

  " Execute the command.
  execute a:command

  " Restore the last search.
  let @/ = search

  " Restore the previous window position.
  call setpos('.', window_position)
  normal! zt

  " Restore the previous cursor position.
  call setpos('.', cursor_position)
endfunction

" Re-indent the whole buffer.
function! Indent()
  call Preserve('normal gg=G')
endfunction

autocmd CursorMovedI <buffer> call Indent()


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

inoremap <Leader>/ <esc>mxA;<esc>`xa
nnoremap <Leader>/ <esc>mxA;<esc>

nnoremap <Leader>0 1gt

autocmd filetype netrw call Netrw_mappings()
function! Netrw_mappings()
    noremap <buffer>% :call CreateInPreview()<cr>
endfunction

function! CreateInPreview()
    let l:filename = input("Please enter filename: ")
    execute 'silent !touch ' . b:netrw_curdir.'/'.l:filename
    redraw!
endf

" Switch to last-active tab
au TabLeave * let g:lasttab = tabpagenr()
nnoremap <silent> <c-l> :exe "tabn ".g:lasttab<cr>
vnoremap <silent> <c-l> :exe "tabn ".g:lasttab<cr>

nnoremap <silent> n   n:call HLNext(0.4)<cr>
nnoremap <silent> N   N:call HLNext(0.4)<cr>

highlight WhiteOnRed ctermbg=red    guibg=red
function! HLNext (blinktime)
    let [bufnum, lnum, col, off] = getpos('.')
    let matchlen = strlen(matchstr(strpart(getline('.'),col-1),@/))
    let target_pat = '\c\%#\%('.@/.'\)'
    let ring = matchadd('WhiteOnRed', target_pat, 101)
    redraw
    exec 'sleep ' . float2nr(a:blinktime * 150) . 'm'
    call matchdelete(ring)
    redraw
    exec 'sleep ' . float2nr(a:blinktime * 150) . 'm'
    let ring = matchadd('WhiteOnRed', target_pat, 101)
    redraw
    exec 'sleep ' . float2nr(a:blinktime * 150) . 'm'
    call matchdelete(ring)
    redraw
    exec 'sleep ' . float2nr(a:blinktime * 150) . 'm'
    let ring = matchadd('WhiteOnRed', target_pat, 101)
    redraw
    exec 'sleep ' . float2nr(a:blinktime * 150) . 'm'
    call matchdelete(ring)
    redraw
endfunction

nnoremap `` :set invnumber<cr>

" Show syntax highlighting groups for word under cursor
nmap <C-S-P> :call <SID>SynStack()<CR>
function! <SID>SynStack()
  if !exists("*synstack")
    return
  endif
  echo map(synstack(line('.'), col('.')), 'synIDattr(v:val, "name")')
endfunc

nnoremap <Leader>y :TagbarToggle<cr>

nnoremap <C-d> "_d
nnoremap <C-D> "_D
