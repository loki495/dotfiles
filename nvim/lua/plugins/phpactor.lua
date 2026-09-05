return {
    "gbprod/phpactor.nvim",
    dependencies = {
        "nvim-lua/plenary.nvim",
    },
    config = function()
        require("phpactor").setup({
            install = {
                -- Resolved via PATH (installed to ~/.local/bin by
                -- scripts/install/80-bin-tools.sh) rather than a hardcoded
                -- path into this repo's own bin/.
                bin = 'phpactor',
            }
        })
    end,
}
