vim.opt.shortmess:append "sI"

vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true

vim.opt.mouse = ""

vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.hlsearch = true
vim.opt.incsearch = true
vim.opt.showmatch = true

vim.opt.nu = true
vim.opt.rnu = true

vim.opt.autoindent = true
vim.opt.smartindent = true

vim.opt.wrap = false

vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undodir = os.getenv("HOME") .. "/.vim/undodir"
vim.opt.undofile = true

vim.opt.termguicolors = true

vim.opt.scrolloff = 8
vim.opt.signcolumn = "yes:1"
vim.opt.isfname:append("@-@")

vim.opt.updatetime = 50
vim.opt.lazyredraw = true
vim.opt.synmaxcol = 240

vim.wo.cursorline = true
vim.opt.colorcolumn = "80"

vim.opt.encoding = "utf-8"
vim.opt.errorbells = false

vim.opt.splitright = true

vim.opt.wildmode = { "longest:full", "full" }  -- break into list, avoids parsing bugs
vim.opt.wildoptions = "pum"
vim.opt.wildchar = 9  -- Tab key
vim.opt.wildmenu = true
