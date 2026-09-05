return {
    "gbprod/phpactor.nvim",
    dependencies = {
        "nvim-lua/plenary.nvim",
    },
    config = function()
        require("phpactor").setup({
            install = {
                -- phpactor.nvim's own check_installed.lua does a literal
                -- Path:exists() on this value, not a PATH lookup - a bare
                -- command name always reads as "not installed" and pops an
                -- interactive prompt (hangs headless nvim, confirmed live in
                -- CI). Must be an actual path, just not one hardcoded into
                -- this repo's own checkout - ~/.local/bin is where
                -- scripts/install/80-bin-tools.sh fetches phpactor to.
                bin = vim.fn.expand('~/.local/bin/phpactor'),
            }
        })
    end,
}
