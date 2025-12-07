vim.api.nvim_create_autocmd("VimLeavePre", {
    callback = function()
        vim.fn.system("pkill -f 'phpactor language-server'")
    end,
})

vim.api.nvim_create_autocmd("BufReadPost", {
  pattern = "*",
  callback = function()
    -- Remove stray CR (^M) characters
    vim.cmd([[%s/\r//ge]])
  end,
})
