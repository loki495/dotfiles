-- Cleared on every load so re-sourcing this file (<leader><leader> while
-- editing it) doesn't register these autocmds a second time.
local group = vim.api.nvim_create_augroup("AndresAutocmds", { clear = true })

vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = function()
        -- pgrep counts this still-running instance too, so <=1 means it's the last one
        local nvim_count = tonumber(vim.fn.system("pgrep -c nvim")) or 0
        if nvim_count <= 1 then
            vim.fn.system("pkill -f 'phpactor language-server'")
        end
    end,
})

vim.api.nvim_create_autocmd("BufReadPost", {
  group = group,
  pattern = "*",
  callback = function()
    -- Remove stray CR (^M) characters
    vim.cmd([[%s/\r//ge]])
  end,
})
