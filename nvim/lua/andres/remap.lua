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

-- Toggle between last buffer and current
vim.keymap.set("n", "<C-l>", ":b#<CR>", { silent = true })

-- Substitute word under cursor
vim.keymap.set("n", "<leader>s", [[:%s/\<<C-r><C-w>\>/<C-r><C-w>/gI<Left><Left><Left>]])

-- Source current file
vim.keymap.set("n", "<leader><leader>", function()
    vim.cmd("so")
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

-- Move line down with N
vim.keymap.set("v", "N", ":m '>+1<CR>gv=gv")

-- Move line up with M
vim.keymap.set("v", "M", ":m '<-2<CR>gv=gv")

-- open file under cursor in new tab with ctrl-t
vim.keymap.set("n", "<C-t>", "<C-w>gf")

-- open current dir in Oil with -
vim.keymap.set("n", "-", ":Oil<CR>")

-- delete word with ctrl-backspace and ctrl-h
vim.keymap.set('i', '<C-BS>', '<C-W>', {noremap = true})
vim.keymap.set('i', '<C-H>',  '<C-W>', {noremap = true})

-- exit terminal mode with ctrl-q
vim.keymap.set('t', '<C-Q>', '<C-\\><C-N>', {noremap = true})

-- show current line diagnistics with <leader><space>
vim.keymap.set('n', '<leader><space>', '<cmd>lua vim.diagnostic.open_float(0, {scope="line"})<CR>')

vim.keymap.set('n', '<leader>q', '<cmd>lua vim.diagnostic.goto_prev()<CR>')
vim.keymap.set('n', '<leader>w', '<cmd>lua vim.diagnostic.goto_next()<CR>')
vim.keymap.set("n", "<leader>e", '<cmd>lua vim.lsp.buf.code_action()<CR>', { silent = true })

vim.keymap.set("n", "Q", 'ZZ', { silent = true })

vim.keymap.set("n", "<leader>p", function()
    vim.cmd("botright split")  -- Open a new horizontal split at the bottom
    vim.cmd("terminal ./vendor/bin/pest " .. vim.fn.expand("%"))  -- Run the CLI command with the current file
end)

vim.filetype.add({
  pattern = { [".*%.blade%.php"] = "php" }
})

vim.api.nvim_set_keymap(
    'n', '<leader>\'\'',
  ":PhpActor import_class<CR>",
  { noremap = true, silent = true }
)
