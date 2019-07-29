set background=dark
if version > 580
	hi clear
	if exists("syntax_on")
		syntax reset
	endif
endif

" Highlight Class and Function names
syn match    tCustomParen    "(" contains=tParen
syn match    tCustomFunc     "\w\+\s*(" contains=tCustomParen
syn match    tCustomScope    "::"
syn match    tCustomClass    "\w\+\s*::" contains=tCustomScope

hi def link tCustomFunc  Function
hi def link tCustomClass Function

set t_Co=256

let g:colors_name = "Scratch"

hi Normal guibg=#242324 guifg=#d4c274
hi CursorLine guibg=#000000 cterm=NONE
hi CursorColumn guibg=#000000

hi vimGroup guifg=#ffff00
hi hiVimGroup guifg=#ff4400
hi vimCommand guifg=#00bb99
hi vimHighlight guifg=#009999

hi IndentGuideDraw guibg=NONE cterm=NONE ctermbg=NONE ctermfg=NONE
hi SpecialKey guibg=NONE cterm=NONE ctermbg=NONE ctermfg=NONE

hi phpStructure guifg=#fff1fa
hi phpInclude guifg=#3ff1fa
hi Statement guifg=#d4c274
hi Function guifg=#ffffff
hi phpIdentifier guifg=#3590a7
hi phpStringSingle guifg=#d5ff00
hi phpStringDouble guifg=#45ff44

hi phpComment guifg=#999999 guibg=NONE
hi phpDocTags guifg=#ffadad guibg=NONE
