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

-- Native treesitter highlighting (nvim-treesitter was archived and dropped -
-- see git log). Neovim 0.12 only bundles c/lua/markdown/vim/query/vimdoc
-- parsers+queries; the rest come from `install_neovim.sh --parsers` plus
-- query files placed under ~/.local/share/nvim/site/queries/<lang>/.
local ft_to_lang = {
    sh = "bash",
    typescriptreact = "tsx",
}
local treesitter_filetypes = {
    "sh", "html", "yaml", "javascript", "typescript",
    "typescriptreact", "vue", "json", "php", "rust", "toml",
}
vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = treesitter_filetypes,
    callback = function(args)
        local lang = ft_to_lang[args.match] or args.match
        pcall(vim.treesitter.start, args.buf, lang)
    end,
})
