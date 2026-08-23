return {
    "Exafunction/codeium.nvim",
    dependencies = {
        "nvim-lua/plenary.nvim",
        "hrsh7th/nvim-cmp",
    },
    config = function()
        require("codeium").setup(
            {
                vim.keymap.set('i', '<C-G>', function () return vim.fn['codeium#Accept']() end, { expr = true, silent = true })
            })
    end
}
