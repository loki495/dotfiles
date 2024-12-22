vim.api.nvim_create_user_command('AndresRunCommand',
    function ()
        local input = vim.fn.getreg('c');
        if not input then return end
        cmd = input .. " " .. vim.api.nvim_buf_get_name(0)

        vim.cmd('vsplit')
        local win = vim.api.nvim_get_current_win()
        local buf = vim.api.nvim_create_buf(true, true)
        vim.api.nvim_win_set_buf(win, buf)

        vim.fn.termopen(cmd)
    end,
    {}
)

vim.api.nvim_create_user_command('AndresPromptCommand',
    function ()
        vim.ui.input({ prompt = "Enter command: " }, function(input)
            if not input then return end
            vim.fn.setreg('c', input)
            vim.cmd("AndresRunCommand")
        end)
    end,
    {}
)

vim.keymap.set('n', '<leader>m', function ()
    vim.cmd("AndresPromptCommand")
end)

vim.keymap.set('n', '<leader>mm', function()
    vim.cmd("AndresRunCommand")
end)


