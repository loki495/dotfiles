return {
    "gbprod/phpactor.nvim",
    dependencies = {
        "nvim-lua/plenary.nvim",
    },
    config = function()
        require("phpactor").setup({
            install = {
                bin = require('andres.phpactor').bin(),
                check_on_startup = 'none',
            },
            -- nvim-lspconfig owns the server settings and completion capabilities.
            lspconfig = { enabled = false },
        })
    end,
}
