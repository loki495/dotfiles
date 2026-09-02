return {
    "luckasRanarison/tailwind-tools.nvim",
    name = "tailwind-tools",
    build = ":UpdateRemotePlugins",
    dependencies = {
        "nvim-telescope/telescope.nvim", -- optional
        "neovim/nvim-lspconfig", -- optional
    },
    opts = {
        cmd = "./node_modules/.bin/tailwindcss",
        config = "./tailwind.config.js",
        include = {"./resources/**/*.{js,vue,jsx,ts,tsx}", "./src/**/*.{js,jsx}"},
        exclude = {"node_modules", "dist"},
        enable_tsx = false,  -- disable TSX parsing
    } -- your configuration
}
