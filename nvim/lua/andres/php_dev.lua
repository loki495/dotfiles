local M = {}

-- Override with $PHP_SRC if your php-src checkout lives somewhere else.
local PHP_SRC = vim.env.PHP_SRC or vim.fn.expand("~/dev/php-src")
M.PHP_SRC = PHP_SRC

function M.build_fast()
  local output = {}
  local errors = {}

  vim.fn.jobstart("make fast_cli", {
    cwd = PHP_SRC,
    stdout_buffered = true,


    on_stdout = function(_, data)
      for _, line in ipairs(data or {}) do
        if line ~= "" then table.insert(output, line) end
      end
    end,

    on_stderr = function(_, data)
      for _, line in ipairs(data or {}) do
        if line ~= "" then table.insert(errors, { filename = filename, lnum = 1, col = 1, text = line }) end
      end
    end,
   
    on_exit = function(_, exit_code)
      if #errors > 0 or exit_code ~= 0 then
        vim.schedule(function()
          vim.fn.setqflist({}, ' ', {
            title = "PHP Compile Errors",
            items = errors,
          })
          vim.cmd("copen | vertical resize 80")
        end)
      else
        vim.schedule(function()
          vim.cmd("vnew")
          local buf = vim.api.nvim_get_current_buf()
          --vim.api.nvim_buf_set_name(buf, "PHP Run Output")
          vim.api.nvim_buf_set_lines(buf, 0, -1, false, output)
          vim.api.nvim_buf_set_option(buf, "modifiable", false)
        end)
      end
      end,
    })
end

function M.toggle_debug_macro()
  vim.fn.jobstart("make toggle-macro", {
    cwd = PHP_SRC,
    stdout_buffered = true,
    on_stdout = function(_, data) print(table.concat(data, "\n")) end,
    on_stderr = function(_, data) print(table.concat(data, "\n")) end
  })
end

function M.run_php_test()
  local pickers = require("telescope.builtin")
  local actions = require("telescope.actions")
  local action_state = require("telescope.actions.state")

  pickers.find_files({
    prompt_title = "Pick PHP Test File",
    cwd = PHP_SRC .. "/php_tests",
    find_command = { "rg", "--files", "--iglob", "*.php", "--hidden" },

    attach_mappings = function(prompt_bufnr, map)
      map("i", "<CR>", function()
        local entry = action_state.get_selected_entry()
        actions.close(prompt_bufnr)

        local filename = entry.path or entry[1]
        local output = {}
        local errors = {}

        StreamCommandInVSplit({ "make", "run", "FILE=" .. filename }, PHP_SRC)
      end)

      return true
    end,
  })
end

return M
