return {
    "gbprod/phpactor.nvim",
    dependencies = {
        "nvim-lua/plenary.nvim",
    },
    config = function()
        require("phpactor").setup({
            install = {
                bin = vim.fn.expand('~/dotfiles/bin/phpactor'),
            }
        })
    end,
}
