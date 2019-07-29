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

" hi Pmenu guibg=#005599 guifg=#f7f5a2
" PmenuSel PmenuThumb PmenuSbar

hi CoCWarningSign guibg=#888800 guifg=#ffffff
hi CoCWarningVirtualText guibg=#888800 guifg=#ffffff
hi CoCWarningLine guibg=#888800 guifg=#ffffff
hi CoCWarningHighlight guibg=#aa0000 guifg=#FFFFFF gui=bold,underline
hi CoCWarningFloat guibg=#888800 guifg=#ffffff
hi CoCInfoSign guibg=#000088 guifg=#ffffff
hi CoCInfoVirtualText guibg=#000088 guifg=#ffffff
hi CoCInfoLine guibg=#000088 guifg=#ffffff
hi CoCInfoHighlight guibg=#aa0000 guifg=#FFFFFF gui=bold,underline
hi CoCInfoFloat guibg=#000088 guifg=#ffffff
hi CoCHintSign guibg=#008800 guifg=#ffffff
hi CoCHintVirtualText guibg=#008800 guifg=#ffffff
hi CoCHintLine guibg=#008800 guifg=#ffffff
hi CoCHintHighlight guibg=#aa0000 guifg=#FFFFFF gui=bold,underline
hi CoCHintFloat guibg=#008800 guifg=#ffffff
hi CoCErrorSign guibg=#880000 guifg=#ffffff
hi CoCErrorVirtualText guibg=#880000 guifg=#ffffff
hi CoCErrorLine guibg=#880000 guifg=#ffffff
hi CoCErrorHighlight guibg=#aa0000 guifg=#FFFFFF gui=bold,underline
hi CoCErrorFloat guibg=#880000 guifg=#ffffff
