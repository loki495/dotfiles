vim.g.mapleader = ","

-- Clear highlighted search results with ENTER
vim.keymap.set("n", "<CR>", [[{-> v:hlsearch ? ":nohl<CR>" : "<CR>"}()]], { silent = true, expr = true })

-- Ctr-C to escape insert
vim.keymap.set("i", "<C-c>", "<Esc>")

-- Check if 4 below necessary / useful
--       paste without overwriting register map?
vim.keymap.set("x", "<leader>p", [["_dP]])
vim.keymap.set({"n", "v"}, "<leader>y", [["+y]])
vim.keymap.set("n", "<leader>Y", [["+Y]])
vim.keymap.set({"n", "v"}, "<leader>d", [["_d]])

-- Quickerror / location list navigation
vim.keymap.set("n", "<C-k>", "<cmd>cnext<CR>zz")
vim.keymap.set("n", "<C-j>", "<cmd>cprev<CR>zz")
vim.keymap.set("n", "<leader>k", "<cmd>lnext<CR>zz")
vim.keymap.set("n", "<leader>j", "<cmd>lprev<CR>zz")

-- Substitute word under cursor
vim.keymap.set("n", "<leader>s", [[:%s/\<<C-r><C-w>\>/<C-r><C-w>/gI<Left><Left><Left>]])

-- Source current file
vim.keymap.set("n", "<leader><leader>", function()
    vim.cmd("so")
end)

-- Launch Navbuddy
vim.keymap.set({"n","x","i"}, "<leader>ee", function ()
    local navbuddy = require("nvim-navbuddy")
    navbuddy.open()
end)

-- Disable arrow key
vim.keymap.set("n", "<up>", "<nop>")
vim.keymap.set("n", "<down>", "<nop>")
vim.keymap.set("n", "<left>", "<nop>")
vim.keymap.set("n", "<right>", "<nop>")
