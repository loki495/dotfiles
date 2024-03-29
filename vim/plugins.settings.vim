"-------Plugins----------

"/
"/ Ag
"/
let g:ackprg = 'ag --nogroup --nocolor --column'

"/
"/ ALE - Lint engine
"/
let g:ale_sign_column_always = 1
let g:ale_completion_enabled = 1
let b:ale_linters = ['remove_trailing_lines','trim_whitespace']

let g:ale_set_quickfix = 1
let g:ale_set_loclist = 1
let g:ale_open_list = 1
nmap <silent> <leader>] :ALENextWrap<cr>
nmap <silent> <leader>[ :ALEPreviousWrap<cr>

let g:ale_php_phpcs_executable='~/dotfiles/bin/phpcs'
let g:ale_php_phpcbf_executable='~/dotfiles/bin/phpcbf-helper.sh'
let g:ale_php_phpcbf_use_global = 1

"/ let g:ale_fixers = {'php': ['phpcbf']}
let g:ale_fix_on_save = 1

"/
"/ IndentLine
"/
let g:indentLine_color_term = 29
let g:indentLine_bgcolor_term = 230

let g:indentLine_char_list = ['|', '|', '|', '┊']
let g:indentLine_enabled = 1

"/
"/ FZF
"/

nmap <Leader>; :GFiles --exclude-standard --others --cached<CR>
nmap <Leader>f :Files<CR>
nmap <Leader>b :Buffers<CR>
nmap <Leader>t :Tags<CR>
nmap <Leader>l :Lines<CR>
nmap <Leader>H :History<cr>
nmap <Leader>a :Rg<cr>

let g:fzf_action = {
  \ 'return': 'tab split',
  \ 'ctrl-e': 'e',
  \ 'ctrl-t': 'tab split',
  \ 'ctrl-x': 'split',
  \ 'ctrl-v': 'vsplit' }

let g:fzf_buffers_jump = 1

let g:fzf_layout = { 'down': '~40%' }

let g:fzf_colors =
\ { 'fg':      ['fg', 'Normal'],
  \ 'bg':      ['bg', 'Normal'],
  \ 'hl':      ['fg', 'Comment'],
  \ 'fg+':     ['fg', 'CursorLine', 'CursorColumn', 'Normal'],
  \ 'bg+':     ['bg', 'CursorLine', 'CursorColumn'],
  \ 'hl+':     ['fg', 'Statement'],
  \ 'info':    ['fg', 'PreProc'],
  \ 'border':  ['fg', 'Ignore'],
  \ 'prompt':  ['fg', 'Conditional'],
  \ 'pointer': ['fg', 'Exception'],
  \ 'marker':  ['fg', 'Keyword'],
  \ 'spinner': ['fg', 'Label'],
  \ 'header':  ['fg', 'Comment'] }


"/
"/ Netrw
"/
let g:netrw_use_errorwindow=0   " suppress error window
let g:netrw_liststyle=3         " thin
let g:netrw_altv=1
let g:netrw_browse_split = 3

"/
"/ SuperTab
"/
let g:SuperTabDefaultCompletionType = "<c-x><c-o>"
let g:SuperTabCompletionContexts = "['s:ContextText']"
let g:SuperTabLongestEnhanced = 1
let g:SuperTabLongestHighlight = 1

"/
"/ PHPComplete
"/
" autocmd FileType php setlocal omnifunc=phpcomplete#CompletePHP

let g:strip_whitespace_confirm=0
let g:strip_whitespace_on_save = 1

"/
"/ RainbowLevels
"/
map <leader>h :RainbowLevelsToggle<cr>

hi! RainbowLevel0 ctermbg=240 guibg=#333333
hi! RainbowLevel1 ctermbg=239 guibg=#333300
hi! RainbowLevel2 ctermbg=238 guibg=#0e1e0e
hi! RainbowLevel3 ctermbg=237 guibg=#3a3a3a
hi! RainbowLevel4 ctermbg=236 guibg=#303030
hi! RainbowLevel5 ctermbg=235 guibg=#262626
hi! RainbowLevel6 ctermbg=234 guibg=#1c1c1c
hi! RainbowLevel7 ctermbg=233 guibg=#121212
hi! RainbowLevel8 ctermbg=232 guibg=#080808


"\         'tagbar': '%{tagbar#currenttag("[%s] ","", "p")}',
let g:lightline = {
      \ 'active': {
      \   'left': [ [ 'mode', 'paste' ], [ 'filename', ], [ 'tagbar' ] ]
      \ },
      \ 'component': {
      \         'tagbar': ' %{tagbar#currenttagtype("%s ", "")} %{tagbar#currenttag("[%s] ","", "p")}',
      \ },
      \ 'component_function': {
      \   'modified': 'LightLineModified',
      \   'readonly': 'LightLineReadonly',
      \   'filename': 'LightLineFilename',
      \   'fileformat': 'LightLineFileformat',
      \   'filetype': 'LightLineFiletype',
      \   'fileencoding': 'LightLineFileencoding',
      \   'mode': 'LightLineMode'}
      \ }
function! LightLineModified()
  return &ft =~ 'help' ? '' : &modified ? '+' : &modifiable ? '' : '-'
endfunction

function! LightLineReadonly()
  return &ft !~? 'help' && &readonly ? 'RO' : ''
endfunction

function! LightLineFilename()
  let fname = expand('%:p')
  return fname == '__Tagbar__' ? g:lightline.fname :
        \ ('' != LightLineReadonly() ? LightLineReadonly() . ' ' : '') .
        \ ('' != fname ? fname : '[No Name]') .
        \ ('' != LightLineModified() ? ' ' . LightLineModified() : '')
endfunction

function! LightLineFileformat()
  return winwidth(0) > 70 ? &fileformat : ''
endfunction

function! LightLineFiletype()
  return winwidth(0) > 70 ? (strlen(&filetype) ? &filetype : 'no ft') : ''
endfunction

function! LightLineFileencoding()
  return winwidth(0) > 70 ? (strlen(&fenc) ? &fenc : &enc) : ''
endfunction

function! LightLineMode()
  let fname = expand('%:t')
  return fname == '__Tagbar__' ? 'Tagbar' :
        \ winwidth(0) > 60 ? lightline#mode() : ''
endfunction
let g:tagbar_status_func = 'TagbarStatusFunc'

function! TagbarStatusFunc(current, sort, fname, ...) abort
    let g:lightline.fname = a:fname
  return lightline#statusline(0)
endfunction

" Vim Fugitive
nmap <leader>gs :G<CR>


"/
"/ Clang-format
"/
autocmd FileType cpp ClangFormatAutoEnable
