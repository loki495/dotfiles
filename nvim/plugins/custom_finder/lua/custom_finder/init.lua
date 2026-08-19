local Popup = require("nui.popup")
local event = require("nui.utils.autocmd").event

local Layout = require("nui.layout")

local top_popup = Popup({ border = "double" })
local bottom_left_popup = Popup({ border = "single" })
local bottom_right_popup = Popup({ border = "single" })

local layout = Layout(
  {
    position = "50%",
    size = {
      width = 80,
      height = 40,
    },
  },
  Layout.Box({
    Layout.Box(top_popup, { size = "40%" }),
    Layout.Box({
      Layout.Box(bottom_left_popup, { size = "50%" }),
      Layout.Box(bottom_right_popup, { size = "50%" }),
    }, { dir = "row", size = "60%" }),
  }, { dir = "col" })
)

layout:mount()

local api = vim.api
 
local M = {}

local state = {
    popup = nil
}

state.popup = Popup({
  enter = true,
  focusable = true,
  border = {
    style = "rounded",
  },
  position = "50%",
  size = {
    width = "80%",
    height = "60%",
  },
})

function cleanup()
  if state.popup then
    state.popup:unmount()
    state.popup = nil
  end
end

-- mount/open the component
state.popup:mount()

-- unmount component when cursor leaves buffer
state.popup:on(event.BufLeave, function()
    cleanup()
end)

state.popup:map("i", "<Esc>", function()
    cleanup()
end, { noremap = true, silent = true })

state.popup:map("n", "<Esc>", function()
    cleanup()
end, { noremap = true, silent = true })

function M.open()
    vim.api.nvim_buf_set_lines(state.popup.bufnr, 0, 1, false, { "Hello World" })
end
 
return M


-- File: lua/custom_finder/init.lua
-- local Popup = require("nui.popup")
-- local Layout = require("nui.layout")
-- local Input = require("nui.input")
-- local event = require("nui.utils.autocmd").event
-- local Job = require("plenary.job")
-- 
-- local api = vim.api
-- 
-- local M = {}
-- 
-- local state = {
  -- filename_input = "",
  -- path_input = "",
  -- file_list = {},
  -- selected_index = 1,
  -- layout = nil,
  -- inputs = {},
  -- windows = {},
-- }
-- 
-- local function fuzzy_match(str, pattern)
  -- local last_pos = 0
  -- for c in pattern:gmatch(".") do
    -- local found = str:lower():find(c:lower(), last_pos + 1)
    -- if not found then return false end
    -- last_pos = found
  -- end
  -- return true
-- end
-- 
-- local function search_files()
  -- Job:new({
    -- command = "rg",
    -- args = { "--files", "--color", "never" },
    -- cwd = ".",
    -- on_exit = function(j)
      -- local results = j:result()
      -- local filtered = {}
      -- for _, path in ipairs(results) do
        -- local filename = path:match("[^/\\]+$") or ""
        -- if (state.filename_input == "" or fuzzy_match(filename, state.filename_input))
            -- and (state.path_input == "" or fuzzy_match(path, state.path_input)) then
          -- table.insert(filtered, path)
        -- end
      -- end
-- 
      -- vim.schedule(function()
        -- state.file_list = filtered
        -- state.selected_index = 1
        -- local file_list_buf = state.windows.file_list.bufnr
        -- local lines = {}
        -- for i, file in ipairs(filtered) do
          -- table.insert(lines, (i == state.selected_index and "> " or "  ") .. file)
        -- end
        -- api.nvim_buf_set_lines(file_list_buf, 0, -1, false, lines)
        -- M.update_preview()
      -- end)
    -- end
  -- }):start()
-- end
-- 
-- function M.update_preview()
  -- local file = state.file_list[state.selected_index]
  -- if not file then return end
  -- local preview_buf = state.windows.preview.bufnr
  -- local lines = {}
  -- local f = io.open(file, "r")
  -- if f then
    -- for _ = 1, 30 do
      -- local line = f:read("*line")
      -- if not line then break end
      -- table.insert(lines, line)
    -- end
    -- f:close()
  -- end
  -- api.nvim_buf_set_lines(preview_buf, 0, -1, false, lines)
-- end
-- 
-- local function cleanup()
  -- if state.layout then
    -- state.layout:unmount()
    -- state.layout = nil
  -- end
-- end
-- 
-- function M.open()
  -- cleanup()
-- 
    -- local file_list_popup = Popup({
        -- enter = false,
        -- focusable = false,
        -- border = "rounded",
        -- title = "Files",
    -- })
    -- local preview_popup = Popup({
        -- enter = false,
        -- focusable = false,
        -- border = "rounded",
        -- title = "Preview",
    -- })
    -- local zzfilename_input = Input({
        -- prompt = "filename: ",
        -- border = "rounded",
    -- }, {
            -- on_change = function(val)
                -- state.filename_input = val
                -- search_files()
            -- end,
        -- })
    -- local path_input = Input({
        -- prompt = "path: ",
        -- border = "rounded",
    -- }, {
            -- on_change = function(val)
                -- state.path_input = val
                -- search_files()
            -- end,
        -- })
-- 
    -- local layout = Layout(
        -- {
            -- position = "50%",
            -- size = { width = 120, height = 30 },
        -- },
        -- Layout.Box({
            -- Layout.Box({
                -- Layout.Box(file_list_popup, { size = "50%" }),
                -- Layout.Box(preview_popup, { size = "50%" }),
            -- }, { size = "85%" }),
            -- Layout.Box({
                -- Layout.Box(filename_input, { size = "50%" }),
                -- Layout.Box(path_input, { size = "50%" }),
            -- }, { size = "15%" }),
        -- }, { dir = "col" })
    -- )
-- 
    -- state.windows.file_list = file_list_popup
    -- state.windows.preview = preview_popup
    -- state.inputs = {
        -- filename = filename_input,
        -- path = path_input,
    -- }
-- 
  -- layout:mount()
  -- filename_input:mount()
  -- path_input:mount()
-- 
  -- state.layout = layout
  -- filename_input:focus()
-- 
  -- local function move_selection(dir)
    -- local new_index = state.selected_index + dir
    -- if new_index >= 1 and new_index <= #state.file_list then
      -- state.selected_index = new_index
      -- local lines = {}
      -- for i, file in ipairs(state.file_list) do
        -- table.insert(lines, (i == state.selected_index and "> " or "  ") .. file)
      -- end
      -- api.nvim_buf_set_lines(file_list.bufnr, 0, -1, false, lines)
      -- M.update_preview()
    -- end
  -- end
-- 
  -- for _, input in pairs(state.inputs) do
    -- input:map("i", "<Up>", function() move_selection(-1) end, { noremap = true, silent = true })
    -- input:map("i", "<Down>", function() move_selection(1) end, { noremap = true, silent = true })
    -- input:map("i", "<Tab>", function()
      -- if vim.api.nvim_get_current_win() == filename_input.winid then
        -- path_input:focus()
      -- else
        -- filename_input:focus()
      -- end
    -- end, { noremap = true, silent = true })
    -- input:map("i", "<CR>", function()
      -- local file = state.file_list[state.selected_index]
      -- if file then
        -- cleanup()
        -- vim.cmd("edit " .. vim.fn.fnameescape(file))
      -- end
    -- end, { noremap = true, silent = true })
    -- input:map("i", "<Esc>", function()
      -- cleanup()
    -- end, { noremap = true, silent = true })
  -- end
-- 
  -- search_files()
-- end
-- 
-- return M
