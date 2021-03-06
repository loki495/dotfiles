"------Mappings----------

" Emmet-vim
" asdsadsasa

" map <C-B> :FufBuffer<CR>

" show all current mappings (in this file)
nnoremap <C-n> :tabnew\|read !vim-mappings<cr>:setlocal buftype=nofile<cr>:setlocal bufhidden=hide<cr>:setlocal noswapfile<cr>

cmap w!! w !sudo tee % >/dev/null

" Switch between the last two files
" nnoremap <Leader><Leader> <C-^>

" Get off my lawn
nnoremap <Left> :echoe "Use h"<CR>
nnoremap <Right> :echoe "Use l"<CR>
nnoremap <Up> :echoe "Use k"<CR>
nnoremap <Down> :echoe "Use j"<CR>

nnoremap <Leader>o R<cr><esc>d0                 "# [Leader-o]    Split line at cursor
nnoremap <Leader>v :set invpaste paste?<CR>     "# [Leader-v]    Toggle paste

imap <C-e> <Esc>e<Space>i                       "# [Ctl-e]    End of word in INSERT MODE

iabbrev cdatal <![CDATA[]]><Left><Left><Left>   "# cdatal    Add CDATA wrappers
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

"------Whitespace removal
highlight ExtraWhitespace ctermbg=red guibg=red

" autocmd BufRead * :%s/\t/    /ge
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

"-------Autocmd--------

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

" Run file as PHP
inoremap <Leader>p :!php %<cr> "# [Leader-p]    run PHP file
noremap <Leader>p :!php %<cr>

"/ CTRL_Backspace delete from cursor to beginning of word
inoremap  <Esc><Right>dbi

" Jump to matching delimiters more easily.
nnoremap <leader><Tab> %
noremap <leader><Tab> %

inoremap <Leader>/ <esc>mxA;<esc>`xa "# [Leader-/]    add semi-colon at end of line
nnoremap <Leader>/ <esc>mxA;<esc>

nnoremap <Leader>0 1gt     "# [Leader-0]    go to first tab

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
nnoremap <silent> <c-u> :exe "tabn ".g:lasttab<cr>    "# [Ctl-u]    toggle last tab
vnoremap <silent> <c-u> :exe "tabn ".g:lasttab<cr>

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

nnoremap <Leader>y :TagbarToggle<cr>

nnoremap <C-d> "_d          "# [Ctrl-d]    delete char without overwriting default register
nnoremap <C-D> "_D          "# [Ctrl-d]    delete rest of line without overwriting default register

" Show syntax highlighting groups for word under cursor
function! <SID>SynStack()
    if !exists("*synstack")
        return
    endif

    " echo map(synstack(line('.'), col('.')), 'synIDattr(v:val, "name")')
    " for id in synstack(line("."), col(".")) echo synIDattr(id, "name") endfor
    echo synIDattr(synID(line("."),col("."),1),"name") . ' -> '
                \ . synIDattr(synID(line("."),col("."),0),"name") . " -> "
                \ . synIDattr(synIDtrans(synID(line("."),col("."),1)),"name")
endfunc


" Toggle ALE quick list
noremap <Leader>q :call QFixToggle()<CR>      "# [Leader-q]    toggle quickfix window

function! QFixToggle()
    if exists("g:qfix_win")
        cclose
        unlet g:qfix_win
    else
        copen 10
        let g:qfix_win = bufnr("$")
    endif
endfunction

function! SyntaxAttr()
    let synid = ""
    let guifg = ""
    let guibg = ""
    let gui   = ""

    let id1  = synID(line("."), col("."), 1)
    let tid1 = synIDtrans(id1)

    if synIDattr(id1, "name") != ""
        let synid = "group: " . synIDattr(id1, "name")
        if (tid1 != id1)
            let synid = synid . '->' . synIDattr(tid1, "name")
        endif
        let id0 = synID(line("."), col("."), 0)
        if (synIDattr(id1, "name") != synIDattr(id0, "name"))
            let synid = synid .  " (" . synIDattr(id0, "name")
            let tid0 = synIDtrans(id0)
            if (tid0 != id0)
                let synid = synid . '->' . synIDattr(tid0, "name")
            endif
            let synid = synid . ")"
        endif
    endif

    " Use the translated id for all the color & attribute lookups; the linked id yields blank values.
    if (synIDattr(tid1, "fg") != "" )
        let guifg = " guifg=" . synIDattr(tid1, "fg") . "(" . synIDattr(tid1, "fg#") . ")"
    endif
    if (synIDattr(tid1, "bg") != "" )
        let guibg = " guibg=" . synIDattr(tid1, "bg") . "(" . synIDattr(tid1, "bg#") . ")"
    endif
    if (synIDattr(tid1, "bold"     ))
        let gui   = gui . ",bold"
    endif
    if (synIDattr(tid1, "italic"   ))
        let gui   = gui . ",italic"
    endif
    if (synIDattr(tid1, "reverse"  ))
        let gui   = gui . ",reverse"
    endif
    if (synIDattr(tid1, "inverse"  ))
        let gui   = gui . ",inverse"
    endif
    if (synIDattr(tid1, "underline"))
        let gui   = gui . ",underline"
    endif
    if (gui != ""                  )
        let gui   = substitute(gui, "^,", " gui=", "")
    endif

    echohl MoreMsg
    let message = synid . guifg . guibg . gui
    if message == ""
        echohl WarningMsg
        let message = "<no syntax group here>"
    endif
    echo message
    echohl None
endfunction

noremap <Leader>p :call SyntaxAttr()<CR>

command! FZFMru call fzf#run({
            \  'source':  v:oldfiles,
            \  'sink':    'e',
            \  'options': '-m -x +s',
            \  'down':    '40%'})

nnoremap <Leader>k :FZFMru<cr>

function! s:DiffWithSaved()               "# [:diffwithsaved]    show buffer differences with last saved version
    let filetype=&ft
    diffthis
    vnew | r # | normal! 1Gdd
    diffthis
    exe "setlocal bt=nofile bh=wipe nobl noswf ro ft=" . filetype
endfunction
com! DiffSaved call s:DiffWithSaved()

" move between tabs
nnoremap <Leader>o gT    "# [Ctl-[]    move to previous tab
nnoremap <Leader>p gt    "# [Ctl-]]    move to next tab

" indent whole file
nnoremap <Leader>= :set lazyredraw<cr>gg=G<C-o><C-o>    "# [Leader-=]    indent whole file
inoremap <Leader>= <esc>:set lazyredraw<cr>magg=G`aa

" search for camelCase or snake_case word delimiters, motions with n-N
noremap <Leader>c mx/[A-Z_]<cr>`x         "# [Leader-c]    search for camelCase and snake_case delimiters, to use with motion n/N

" close tab on ctl-q
nnoremap <C-x> :q<cr>  "# [Ctl-x]    close tab

" autosave delay, cursorhold trigger, default: 4000ms
setl updatetime=50

" highlight the word under cursor (CursorMoved is inperformant)
highlight WordUnderCursor ctermbg=233 cterm=none gui=none
autocmd CursorMoved,CursorHold * call HighlightCursorWord()
function! HighlightCursorWord()
    " if hlsearch is active, don't overwrite it!
    let search = getreg('/')
    let cword = expand('<cword>')
    if match(cword, search) == -1
        exe printf('match WordUnderCursor /\V\<%s\>/', escape(cword, '/\'))
    endif
endfunction

"
" fix syntax highlighting
syntax sync fromstart
au BufEnter *.* :syntax sync fromstart

nnoremap U :syntax on<cr>:syntax sync fromstart<cr>:redraw!<cr>   "# [U]    Fix syntax highlighting

nnoremap <leader>zv :normal mazMzv`a<CR>    "# [Leader-zv]    Close all folds except current

command! Tn -complete=file tabnew
noremap <leader>gf :tabnew <cfile><cr>

function Dos2Unix()
    silent! %s///g
    silent! %s///g
    normal gg
endfunction

au BufReadPost * silent! call Dos2Unix()
