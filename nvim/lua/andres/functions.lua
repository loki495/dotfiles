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

vim.api.nvim_create_user_command('AndresRebaseDiff',
    function ()
        local line = vim.api.nvim_get_current_line()

        -- Split the line into words using Lua's pattern matching
        local words = {}
        for word in string.gmatch(line, "%S+") do
            table.insert(words, word)
        end

        -- Get the second word (if it exists)
        local second_word = words[2]
        if not second_word then
            vim.notify("No second word found", vim.log.levels.WARN)
            return
        end

        local cmd = "git show -p " .. second_word
        vim.notify(second_word, vim.log.levels.INFO);

        local output = vim.fn.systemlist(cmd)

        local buf = vim.api.nvim_create_buf(false, true) -- no file, scratch buffer
        vim.api.nvim_buf_set_lines(buf, 0, -1, false, output)

        local width = math.max(50, vim.o.columns - 20)
        local height = math.min(#output + 2, vim.o.lines - 6)
        local row = math.floor((vim.o.lines - height) / 2)
        local col = math.floor((vim.o.columns - width) / 2)

        local opts = {
            style = "minimal",
            relative = "editor",
            width = width,
            height = height,
            row = row,
            col = col,
            border = "rounded",
        }

        vim.api.nvim_open_win(buf, true, opts)
    end,
    {}
)

vim.keymap.set('n', '<leader>d', function ()
    vim.cmd("AndresRebaseDiff")
end)
