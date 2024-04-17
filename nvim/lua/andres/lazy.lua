local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end

vim.opt.rtp:prepend(lazypath)

require("lazy").setup({

	'sainnhe/gruvbox-material',

	{
		'nvim-treesitter/nvim-treesitter',
		build = ':TSUpdate'
	},

    'gelguy/wilder.nvim',

	'nvim-treesitter/playground',

	'mbbill/undotree',

	'tpope/vim-fugitive',

    'vijaymarupudi/nvim-fzf',

	'ThePrimeagen/harpoon',

    'nvim-lua/plenary.nvim',

    'nvim-treesitter/nvim-treesitter-context',

    {
        'nvim-telescope/telescope.nvim',
            "--branch=stable", -- latest stable release

        -- or                            , branch = '0.1.x',
        dependencies = { {'nvim-lua/plenary.nvim'} }
    },

    {
        'nvim-telescope/telescope-fzf-native.nvim',
        build = 'make'
    },

    {
        "windwp/nvim-autopairs",
        config = function()
                    require("nvim-autopairs").setup {}
        end
    },

    {
        'VonHeikemen/lsp-zero.nvim',
        version = 'v2.x',
        dependencies = {
            -- LSP Support
            'neovim/nvim-lspconfig',             -- Required

            {                                      -- Optional
                'williamboman/mason.nvim',
                build = function()
                    pcall(vim.cmd, 'MasonUpdate')
                end,
            },

            {'williamboman/mason-lspconfig.nvim'}, -- Optional

            -- Autocompletion
            {'hrsh7th/nvim-cmp'},     -- Required
            {'hrsh7th/cmp-nvim-lsp'}, -- Required
            {'L3MON4D3/LuaSnip'},     -- Required
            {'hrsh7th/cmp-buffer'},
        },
    },

    {
        "SmiteshP/nvim-navbuddy",
        dependencies = {
            "neovim/nvim-lspconfig",
            "SmiteshP/nvim-navic",
            "MunifTanjim/nui.nvim",
            "numToStr/Comment.nvim",        -- Optional
            "nvim-telescope/telescope.nvim" -- Optional
        },
    },

    {
        'Exafunction/codeium.vim',
        event = 'BufEnter'
    },

    {
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

})
