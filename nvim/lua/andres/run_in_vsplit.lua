-- nvim/lua/andres/run_in_vsplit.lua
local M = {}

local last_cmd = nil

--- Get the rightmost window in the current tabpage
local function get_rightmost_window()
  local wins = vim.api.nvim_tabpage_list_wins(0)
  local right_win = nil
  local max_col = -1
  for _, w in ipairs(wins) do
    local _, col = unpack(vim.api.nvim_win_get_position(w))
    if col > max_col then
      max_col = col
      right_win = w
    end
  end
  return right_win
end

function M.run(cmd)
  if not cmd or cmd == "" then
    if not last_cmd then
      print("No previous command to run.")
      return
    end
    cmd = last_cmd
  else
    last_cmd = cmd
  end

  local cur_win = vim.api.nvim_get_current_win()
  local right_win = get_rightmost_window()

  -- If rightmost window is not the current window, reuse it; else create a new vsplit
  if right_win ~= cur_win then
    vim.api.nvim_set_current_win(right_win)
  else
    vim.cmd("rightbelow vsplit")
  end

  -- Run the terminal (replaces buffer automatically)
  vim.cmd("terminal " .. cmd)
  vim.cmd("stopinsert")

  -- Return focus to original window
  vim.api.nvim_set_current_win(cur_win)
end

return M

