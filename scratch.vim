sy on
syntax reset
set background=dark

" Highlight Class and Function names
" syn match    tCustomParen    "(" contains=tParen
" syn match    tCustomFunc     "\w\+\s*(" contains=tCustomParen
" syn match    tCustomScope    "::"
" syn match    tCustomClass    "\w\+\s*::" contains=tCustomScope

" hi def link tCustomFunc  Function
" hi def link tCustomClass Function

syn match customFuncAndres /\v[[:alpha:]_.]+\ze(\s?\()/ contained
hi customFuncAndres guibg=#ffffff guifg=#00ff00

hi def link customFuncAndres phpFunctions


set t_Co=256

hi Normal guibg=#1f1f1f guifg=#c4c294
hi CursorLine guibg=#000000 cterm=NONE
hi CursorColumn guibg=#000000 guifg=#000000

hi vimGroup guifg=#ffff77
hi hiVimGroup guifg=#ff4400
hi vimCommand guifg=#00bb99
hi vimHighlight guifg=#00f999
hi Search guibg=#9ff353 guifg=#000000
hi IncSearch guibg=#ad0303 guifg=#e6cb7e

hi IndentGuideDraw guibg=NONE cterm=NONE ctermbg=NONE ctermfg=NONE
hi SpecialKey guibg=NONE cterm=NONE ctermbg=NONE ctermfg=NONE

hi phpStructure guifg=#ff9695
hi phpInclude guifg=#ff919a
hi Statement guifg=#f4f274
hi Function guifg=#ff9695
hi phpIdentifier guifg=#35a0d7
hi phpStringSingle guifg=#d5ff50
hi phpStringDouble guifg=#85ff44
hi phpComment guifg=#999999 guibg=NONE
hi phpDocTags guifg=#ffadad guibg=NONE

hi Pmenu guibg=#005599 guifg=#f7f5a2
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

hi Folded guibg=#555555 guifg=#dddddd

hi TabLineFill guifg=#000000 guibg=#000000
hi TabLine guifg=#d4c274 guibg=#333333 gui=NONE
hi TabLineSel guifg=#333333 guibg=#d4c274

hi LineNr guifg=#656532
hi CursorLineNr guifg=#ffff99
