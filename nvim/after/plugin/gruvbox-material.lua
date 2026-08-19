-- setup must be called before loading the colorscheme
-- Default options:
-- require("gruvbox-material").setup({
--  undercurl = true,
--  underline = true,
--  bold = true,
--  italic = {
--      comments = true
--  },
--  strikethrough = true,
--  invert_selection = false,
--  invert_signs = false,
--  invert_tabline = false,
--  invert_intend_guides = false,
--  inverse = true, -- invert background for search, diffs, statuslines and errors
--  contrast = "", -- can be "hard", "soft" or empty string
--  palette_overrides = {},
--  overrides = {},
--  dim_inactive = false,
--  transparent_mode = false,
--})
vim.g.gruvbox_material_foreground = 'material'
vim.g.gruvbox_material_background = 'hard'     
vim.g.gruvbox_material_enable_bold = 1
vim.g.gruvbox_material_enable_italic = 1
vim.g.gruvbox_material_transparent_background = 0
vim.cmd("colorscheme gruvbox-material")

vim.cmd("colorscheme gruvbox-material")

-- Custom darker background
vim.api.nvim_set_hl(0, "Normal", { bg = "#0d0d0d" })        -- main editor
vim.api.nvim_set_hl(0, "NormalNC", { bg = "#0d0d0d" })      -- inactive windows
vim.api.nvim_set_hl(0, "SignColumn", { bg = "#0d0d0d" })
vim.api.nvim_set_hl(0, "VertSplit", { bg = "#0d0d0d" })
vim.api.nvim_set_hl(0, "StatusLine", { bg = "#1a1a1a" })
vim.api.nvim_set_hl(0, "TabLineFill", { bg = "#1a1a1a" })
vim.api.nvim_set_hl(0, "EndOfBuffer", { bg = "#0d0d0d" })    -- removes ~ background

-- Optional: transparent floating/popup windows
vim.api.nvim_set_hl(0, "NormalFloat", { bg = "#000000" })
vim.api.nvim_set_hl(0, "FloatBorder", { bg = "#121212" })
vim.api.nvim_set_hl(0, "Pmenu", { bg = "#121212" })
