local telescope = require('telescope')
telescope.load_extension("live_grep_args")

local builtin = require('telescope.builtin')

vim.keymap.set('n', '<leader>ff', function()
  require("telescope.builtin").find_files({
    hidden = true,
  })
end, { desc = "Find files (including hidden)" })
vim.keymap.set('n', '<leader>;', builtin.git_files, {})
vim.keymap.set('n', '<leader>fg', ":lua require('telescope').extensions.live_grep_args.live_grep_args()<CR>", {})
vim.keymap.set('n', '<leader>fb', builtin.buffers, {})
vim.keymap.set('n', '<leader>fq', builtin.quickfix, {})
vim.keymap.set('n', '<leader>fd', builtin.diagnostics, {})
vim.keymap.set('n', '<leader>fh', builtin.oldfiles, {})
vim.keymap.set('n', '<leader>ft', builtin.treesitter, {})
vim.keymap.set('n', '<leader>fs', function()
	builtin.grep_string({ search = vim.fn.input("Grep > ") });
end)
vim.keymap.set("n", "<leader>gg", function()
  require("telescope.builtin").current_buffer_fuzzy_find({
    prompt_title = "Fuzzy Search Current File",
    sorter = require("telescope.config").values.generic_sorter({}),
  })
end, { desc = "Fuzzy find in current buffer" })

