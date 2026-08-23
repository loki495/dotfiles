vim.api.nvim_create_autocmd("VimLeavePre", {
    callback = function()
        -- pgrep counts this still-running instance too, so <=1 means it's the last one
        local nvim_count = tonumber(vim.fn.system("pgrep -c nvim")) or 0
        if nvim_count <= 1 then
            vim.fn.system("pkill -f 'phpactor language-server'")
        end
    end,
})

vim.api.nvim_create_autocmd("BufReadPost", {
  pattern = "*",
  callback = function()
    -- Remove stray CR (^M) characters
    vim.cmd([[%s/\r//ge]])
  end,
})
