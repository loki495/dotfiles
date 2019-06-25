"-------Plugins----------

" airline
let g:airline_theme='murmur'
let g:airline_powerline_fonts = 1
let g:Powerline_symbols='unicode'

let g:html_indent_tags = 'li\|p'

if !exists('g:airline_symbols')
    let g:airline_symbols = {}
endif

let g:airline_symbols.space = "\ua0"
let g:airline_powerline_fonts = 1


" unicode symbols
" let g:airline_left_sep = ''
" let g:airline_left_sep = ''
" let g:airline_right_sep = ''
" let g:airline_right_sep = ''
" let g:airline_symbols.linenr = ''
" let g:airline_symbols.linenr = ''
" let g:airline_symbols.linenr = ''
" let g:airline_symbols.branch = ''
" let g:airline_symbols.paste = 'ρ'
" let g:airline_symbols.paste = 'Þ'
" let g:airline_symbols.paste = ''
" let g:airline_symbols.whitespace = 'Ξ'

" airline symbols
" let g:airline_left_sep = ''
" let g:airline_left_alt_sep = ''
" let g:airline_right_sep = ''
" let g:airline_right_alt_sep = ''
" let g:airline_symbols.branch = ''
" let g:airline_symbols.readonly = ''
" let g:airline_symbols.linenr = ''

" Set this. Airline will handle the rest.
let g:airline#extensions#ale#enabled = 1
let g:airline#extensions#tabline#formatter = 'unique_tail_improved'




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
"/ Powerline
"/
let g:Powerline_colorscheme = 'murmur' " Powerline colorscheme

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
autocmd FileType php setlocal omnifunc=phpcomplete#CompletePHP

let g:strip_whitespace_confirm=0
let g:strip_whitespace_on_save = 1

"/
"/ Auto-Pairs
"/
let g:AutoPairsFlyMode = 1
let g:AutoPairsShortcutBackInsert = '<Leader>e'
let g:AutoPairsShortcutJump = '<Leader>w'

" function GetFooText()
  " let line = search('^class', 'ncbW')
  " if line
    " return '' . matchstr(getline(line), '^class \k\+')
  " endif
  " return 'No Class'
" endfunction

" call airline#parts#define_function('foo', 'GetFooText')
" let g:airline_section_z = airline#section#create_right(['ffenc','foo'])

let g:airline#extensions#tagbar#enabled = 1
let g:airline#extensions#tagbar#flags = 'f'  " show full tag hierarchy
