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

-- Tab / Quickerror / location list navigation
vim.keymap.set("n", "<C-;>", ":tabprev<CR>", { silent = true })
vim.keymap.set("n", "<C-'>", ":tabnext<CR>", { silent = true })
vim.keymap.set("n", "<C-k>", "<cmd>cnext<CR>zz", { silent = true })
vim.keymap.set("n", "<C-j>", "<cmd>cprev<CR>zz", { silent = true })
vim.keymap.set("n", "<leader>k", "<cmd>lnext<CR>zz", { silent = true })
vim.keymap.set("n", "<leader>j", "<cmd>lprev<CR>zz", { silent = true })

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

-- Center view horizontally around cursor in current line
vim.keymap.set("n", "<leader>z", "zszH")

-- surround visual selection with special chars
vim.keymap.set("v", "{", "<esc>`>a<cr>}<esc>`<i{<cr><esc>[{iif () <esc>==f{=%F(a")
vim.keymap.set("v", "(", "<esc>I(<esc>A)<esc>")
vim.keymap.set("v", "\"", "<esc>`>a\"<esc>`<i\"<esc>[\"i")
vim.keymap.set("v", "'", "<esc>`>a'<esc>`<i'<esc>[\"i")

-- Move line down
vim.keymap.set("v", "N", ":m '>+1<CR>gv=gv")

-- Move line up
vim.keymap.set("v", "M", ":m '<-2<CR>gv=gv")

-- open file under cursor in new tab
vim.keymap.set("n", "<C-t>", "<C-w>gf")

-- open current dir in Oil
vim.keymap.set("n", "-", ":Oil<CR>")
