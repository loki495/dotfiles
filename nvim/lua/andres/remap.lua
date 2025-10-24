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
vim.keymap.set({"n","i"}, "<leader><leader>", function()
    local file = vim.api.nvim_buf_get_name(0)

    if file:match("^" .. vim.fn.expand("~/.config/nvim/lua/")) or file:match("^" .. vim.fn.expand("~/dotfiles/nvim/lua/")) then
        -- If the file is in your config/lua folder, source it
        vim.cmd("source " .. vim.fn.fnameescape(file))
        print("Sourced: " .. file)
    else
        -- Otherwise, just save the file
        vim.cmd("write")
    end
end, { desc = "Source or save file" })

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

vim.keymap.set('n', '<leader>.',  function()
    local file = vim.fn.expand("%:p")     -- full path to current file
  local ext  = vim.fn.expand("%:e")     -- file extension

  local cmd
  if ext == "php" then
    cmd = "php " .. vim.fn.fnameescape(file)
  elseif ext == "py" then
    cmd = "python " .. vim.fn.fnameescape(file)
  elseif ext == "js" then
    cmd = "node " .. vim.fn.fnameescape(file)
  else
    print("No runner defined for ." .. ext .. " files")
    return
  end

  -- open in a split terminal
  vim.cmd("split term://" .. cmd)
end, { desc = "Run current PHP file in terminal" })

vim.keymap.set("n", "Q", function()
  local buftype = vim.api.nvim_buf_get_option(0, "buftype")
  local name    = vim.api.nvim_buf_get_name(0)

  -- buffers you can't/shouldn't save
  if buftype ~= "" then
    vim.cmd("q")  -- just close terminal, help, quickfix, etc.
  elseif name ~= "" then
    vim.cmd("wq") -- normal file buffer
  else
    vim.cmd("q!") -- unnamed buffer
  end
end, { noremap = true, silent = true })

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

vim.api.nvim_set_keymap(
    'n', '<leader><S-C>',
    ":CodeCompanionChat<CR>",
  { noremap = true, silent = true }
)

local php_dev = require("andres.php_dev")

vim.keymap.set("n", "<leader>cc", function()
  StreamCommandInVSplit({ "make", "fast_cli" }, "/home/andres/dev/php-src")
end, { desc = "Build PHP with Highlighting" })

vim.keymap.set("n", "<leader>cv", php_dev.run_php_test, { desc = "Pick + run PHP test" })
vim.keymap.set("n", "<leader>cd", php_dev.toggle_debug_macro, { desc = "Toggle MY_DEBUG macro" })

vim.keymap.set("n", "<leader>vv", ToggleVSplitWidth, { desc = "Toggle VSplit Width (90%/50%)" })

vim.keymap.set("n", "<leader>t", ':tabnew<CR>', { silent = true })

pcall(vim.keymap.del, "n", "<C-W><C-D>")
pcall(vim.keymap.del, "n", "<C-W>d")
vim.keymap.set("n", "<C-W>", '<C-W><C-W>', { desc = "Toggle VSplit Width (90%/50%)" })

local run = require("andres.run_in_vsplit")

vim.keymap.set("n", "<leader>m", function()
  local cmd = vim.fn.input("Command: ")
  run.run(cmd)
end, { desc = "Run shell command in right vsplit" })

