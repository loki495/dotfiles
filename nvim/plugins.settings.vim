"-------Plugins----------

"" airline
let g:airline_theme='murmur'
let g:airline_powerline_fonts = 1
let g:Powerline_symbols='unicode'

let g:html_indent_tags = 'li\|p'

if !exists('g:airline_symbols')
    let g:airline_symbols = {}
endif

let g:airline_symbols.space = "\ua0"
let g:airline_powerline_fonts = 1

set listchars=trail:·,precedes:«,extends:»

let g:airline#extensions#tagbar#enabled = 1
let g:airline#extensions#tagbar#flags = 'f'  " show full tag hierarchy

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
" let g:airline#extensions#ale#enabled = 1
" let g:airline#extensions#tabline#formatter = 'unique_tail_improved'

"/
"/ Powerline
"/
let g:Powerline_colorscheme = 'murmur' " Powerline colorscheme

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
  \ 'ctrl-t': 'tab split',
  \ 'ctrl-x': 'split',
  \ 'ctrl-v': 'vsplit' }

let g:fzf_layout = { 'window': '-tabnew' }

let g:fzf_buffers_jump = 1

"/
"/ Netrw
"/
let g:netrw_use_errorwindow=0   " suppress error window
let g:netrw_liststyle=3         " thin
let g:netrw_altv=1
let g:netrw_browse_split = 3


