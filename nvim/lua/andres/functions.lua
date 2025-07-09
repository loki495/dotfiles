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


-- Global variable to track which window is currently wide (90%)
local last_wide_win = nil

function ToggleVSplitWidth()
  local total_columns = vim.o.columns
  local target_width

  if last_wide_win then
    target_width = math.floor(total_columns * 0.5)
    last_wide_win = nil
  else
    local current_win = vim.api.nvim_get_current_win()
    target_width = math.floor(total_columns * 0.9)
    last_wide_win = current_win
  end

  vim.cmd("vertical resize " .. target_width)
end

function ToggleVSplitTo90()
  if not last_wide_win then
    return
  end

  local total_cols = vim.o.columns
  local current_win = vim.api.nvim_get_current_win()
  local wide_width = math.floor(total_cols * 0.9)
  local normal_width = math.floor(total_cols * 0.5)

  -- Check if the current window is already at 90% width
  local current_win_width = vim.api.nvim_win_get_width(current_win)

  if current_win_width == wide_width then
    -- If it's already at 90%, do nothing
    return
  end

  -- If there was a previous wide window and it's not the current one, shrink it
  if last_wide_win and vim.api.nvim_win_is_valid(last_wide_win) and last_wide_win ~= current_win then
    vim.api.nvim_set_current_win(last_wide_win)
    vim.cmd("vertical resize " .. normal_width)
  end

  -- Resize the focused window to 90%
  vim.api.nvim_set_current_win(current_win)
  vim.cmd("vertical resize " .. wide_width)

  -- Update the last wide window
  last_wide_win = current_win
end

-- Create an autocommand that triggers on window enter.
vim.api.nvim_create_autocmd("WinEnter", {
  callback = function()
    ToggleVSplitTo90()
  end,
})

function StreamCommandInVSplit(cmd, cwd)
  vim.cmd("vnew")
  local buf = vim.api.nvim_get_current_buf()
  local win = vim.api.nvim_get_current_win()

  vim.api.nvim_buf_set_name(buf, "Build Output")
  vim.api.nvim_buf_set_option(buf, "buftype", "nofile")
  vim.api.nvim_buf_set_option(buf, "bufhidden", "wipe")
  vim.api.nvim_buf_set_option(buf, "swapfile", false)
  vim.api.nvim_buf_set_option(buf, "modifiable", true)
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, { "[Compiling...]" })

  vim.wo.number = false
  vim.wo.relativenumber = false
  vim.wo.wrap = false

  -- Setup highlights
  vim.api.nvim_set_hl(0, "BuildError", { fg = "#ff5555", bold = true })
  vim.api.nvim_set_hl(0, "BuildWarning", { fg = "#f1c40f", bold = true })
  vim.api.nvim_set_hl(0, "BuildNote", { fg = "#5fd7ff" })

  local function highlight_line(line_num, line)
    if line:match("[Ee]rror") then
      vim.api.nvim_buf_add_highlight(buf, -1, "BuildError", line_num, 0, -1)
    elseif line:match("[Ww]arning") then
      vim.api.nvim_buf_add_highlight(buf, -1, "BuildWarning", line_num, 0, -1)
    elseif line:match("[Nn]ote") then
      vim.api.nvim_buf_add_highlight(buf, -1, "BuildNote", line_num, 0, -1)
    end
  end

  local function append_lines(lines)
    if not lines or vim.api.nvim_buf_is_valid(buf) == false then return end

    vim.schedule(function()
      local current_line_count = vim.api.nvim_buf_line_count(buf)
      vim.api.nvim_buf_set_option(buf, "modifiable", true)
      vim.api.nvim_buf_set_lines(buf, -1, -1, false, lines)
      for i, line in ipairs(lines) do
        highlight_line(current_line_count + i - 1, line)
      end
      vim.api.nvim_buf_set_option(buf, "modifiable", false)
      vim.api.nvim_win_set_cursor(win, { vim.api.nvim_buf_line_count(buf), 0 })
    end)
  end

  vim.fn.jobstart(cmd, {
    cwd = cwd,
    stdout_buffered = false,
    stderr_buffered = false,
    on_stdout = function(_, data)
      append_lines(data)
    end,
    on_stderr = function(_, data)
      append_lines(data)
    end,
    on_exit = function(_, code)
      append_lines({ "", "[Build finished with exit code " .. code .. "]" })
    end,
  })
end


