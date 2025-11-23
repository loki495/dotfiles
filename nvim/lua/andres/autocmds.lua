vim.api.nvim_create_autocmd("VimLeavePre", {
    callback = function()
        vim.fn.system("pkill -f 'phpactor language-server'")
    end,
})

