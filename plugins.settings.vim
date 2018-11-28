let g:deoplete#enable_at_startup = 1
if !exists('g:deoplete#omni#input_patterns')
  let g:deoplete#omni#input_patterns = {}
endif
" let g:deoplete#disable_auto_complete = 1
autocmd InsertLeave,CompleteDone * if pumvisible() == 0 | pclose | endif

" deoplete tab-complete
inoremap <expr><tab> pumvisible() ? "\<c-n>" : "\<tab>"
autocmd FileType php let g:SuperTabDefaultCompletionType = "<c-x><c-o>"
let g:UltiSnipsExpandTrigger="<C-j>"
"-------Plugins----------

" vim-root
let g:rooter_manual_only = 1
function! s:find_git_root()
  return system('git rev-parse --show-toplevel 2> /dev/null')[:-2]
endfunction

command! ProjectFiles execute 'Files' s:find_git_root()


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

" Set this. Airline will handle the rest.
let g:airline#extensions#ale#enabled = 1



"/
"/ Ag
"/
let g:ackprg = 'ag --nogroup --nocolor --column'

"/
"/ ALE - Lint engine
"/
let g:ale_sign_column_always = 1
let g:ale_completion_enabled = 1

" nmap <silent> <Leader>[ <Plug>(ale_previous_wrap)
" nmap <silent> <Leader>] <Plug>(ale_next_wrap)

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
nmap ; :Files<CR>
nmap <Leader>b :Buffers<CR>
nmap <Leader>t :Tags<CR>
nmap <Leader>l :Lines<CR>
nmap <Leader>. :History<cr>
nmap <Leader>, :Windows<cr>

let g:fzf_action = {
  \ 'ctrl-t': 'tab split',
  \ 'ctrl-x': 'split',
  \ 'ctrl-v': 'vsplit' }


let g:fzf_buffers_jump = 1

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
" nmap <Leader>1 :NERDTreeToggle<cr>
" let NERDTreeHijackNetrw = 1
" let NERDTreeChDirMode=0

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
" let Tlist_Use_Right_Window=1
" let Tlist_Auto_Update = 1
" let Tlist_Close_On_Select = 0
" let Tlist_GainFocus_On_ToggleOpen = 0
" let Tlist_Auto_Open=1
" let Tlist_Enable_Fold_Column=0
" let Tlist_Compact_Format=1
" let Tlist_WinWidth=40
" let Tlist_Exit_OnlyWindow=1
" let Tlist_File_Fold_Auto_Close = 1

" nnoremap <silent> <F8> :TlistToggle<CR>
" autocmd CursorMoved *.php :TlistUpdate
" autocmd CursorMovedI *.php :TlistUpdate

"/
"/ Tagbar
"/

nmap <F8> :TagbarToggle<CR>
let g:airline#extensions#tagbar#flags = 'f'  " show full tag hierarchy
