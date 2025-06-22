local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local out = vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
  if vim.v.shell_error ~= 0 then
    vim.api.nvim_echo({
      { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
      { out, "WarningMsg" },
      { "\nPress any key to exit..." },
    }, true, {})
    vim.fn.getchar()
    os.exit(1)
  end
end

vim.opt.rtp:prepend(lazypath)

require("lazy").setup({

	'sainnhe/gruvbox-material',

	{
		'nvim-treesitter/nvim-treesitter',
		build = ':TSUpdate'
	},

	'nvim-treesitter/playground',

	'mbbill/undotree',

	'tpope/vim-fugitive',

    'vijaymarupudi/nvim-fzf',

	'ThePrimeagen/harpoon',

    'nvim-lua/plenary.nvim',

    'gelguy/wilder.nvim',

    'nvim-treesitter/nvim-treesitter-context',

    {
        'nvim-telescope/telescope.nvim',
            --"--branch=stable", -- latest stable release

        -- or                            , branch = '0.1.x',
        dependencies = {
            {
                'nvim-lua/plenary.nvim'
            },
            {
                "nvim-telescope/telescope-live-grep-args.nvim" ,
                -- This will not install any breaking changes.
                -- For major updates, this must be adjusted manually.
                version = "^1.0.0",
            },
        }
    },

    {
        'romgrk/fzy-lua-native',
        build = 'make',
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
    },

    {
        'neovim/nvim-lspconfig',
        dependencies = {
            -- Mason for managing LSP servers
            'williamboman/mason.nvim',
            'williamboman/mason-lspconfig.nvim',

            -- Completion dependencies
            'hrsh7th/nvim-cmp',
            'hrsh7th/cmp-nvim-lsp',
            'hrsh7th/cmp-buffer',
            'L3MON4D3/LuaSnip',
            'saadparwaiz1/cmp_luasnip',
        },
        config = function()
            -- Set up Mason first
            require('mason').setup({
                ui = {
                    icons = {
                        package_installed = "✓",
                        package_pending = "➜",
                        package_uninstalled = "✗"
                    }
                }
            })


            -- Configure LSP capabilities for nvim-cmp
            local capabilities = require('cmp_nvim_lsp').default_capabilities()

            -- Configure phpactor specifically for auto-imports
            require('lspconfig').phpactor.setup({
                capabilities = capabilities,
                init_options = {
                    ["language_server_phpstan.enabled"] = false,
                    ["language_server_psalm.enabled"] = false,
                    ["indexer.enabled"] = true, -- Enable indexing for imports
                    ["code_transform.import_globals"] = true, -- Enable auto-imports
                },
                handlers = {
                    -- Setup handler for code actions
                    ["textDocument/codeAction"] = function(_, result, ctx, _)
                        if result == nil or vim.tbl_isempty(result) then
                            return
                        end
                        -- Handle code actions (where auto-imports would appear)
                        local client = vim.lsp.get_client_by_id(ctx.client_id)
                        return require('vim.lsp.handlers').code_action(_, result, ctx, _)
                    end,
                }
            })


            -- Configure keymaps
            vim.api.nvim_create_autocmd('LspAttach', {
                group = vim.api.nvim_create_augroup('UserLspConfig', {}),
                callback = function(ev)
                    local opts = { buffer = ev.buf }

                    -- LSP actions
                    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts)
                    vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts)
                    vim.keymap.set('n', '<leader>vws', vim.lsp.buf.workspace_symbol, opts)
                    vim.keymap.set('n', '<leader>vd', vim.diagnostic.open_float, opts)
                    vim.keymap.set('n', '[d', vim.diagnostic.goto_next, opts)
                    vim.keymap.set('n', ']d', vim.diagnostic.goto_prev, opts)
                    vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, opts)
                    vim.keymap.set('n', '<leader>rr', vim.lsp.buf.references, opts)
                    vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts)
                    vim.keymap.set('i', '<C-h>', vim.lsp.buf.signature_help, opts)
                end,
            })
        end
    },

    {
        'hrsh7th/nvim-cmp',
        dependencies = {
            'L3MON4D3/LuaSnip',
            'saadparwaiz1/cmp_luasnip',
            'hrsh7th/cmp-nvim-lsp',
            'hrsh7th/cmp-buffer',
            'hrsh7th/cmp-path',
            'hrsh7th/cmp-cmdline',
        },
        config = function()
            local cmp = require('cmp')
            local luasnip = require('luasnip')

            cmp.setup({
                snippet = {
                    expand = function(args)
                        luasnip.lsp_expand(args.body)
                    end,
                },
                window = {
                    completion = cmp.config.window.bordered(),
                    documentation = cmp.config.window.bordered(),
                },
                mapping = cmp.mapping.preset.insert({
                    ['<C-p>'] = cmp.mapping.select_prev_item(),
                    ['<C-n>'] = cmp.mapping.select_next_item(),
                    ['<C-b>'] = cmp.mapping.scroll_docs(-4),
                    ['<C-f>'] = cmp.mapping.scroll_docs(4),
                    ['<C-Space>'] = cmp.mapping.complete(),
                    ['<C-e>'] = cmp.mapping.abort(),
                    ['<CR>'] = cmp.mapping.confirm({ select = true }),
                    ['<Tab>'] = cmp.mapping(function(fallback)
                        if cmp.visible() then
                            cmp.select_next_item()
                        elseif luasnip.expand_or_jumpable() then
                            luasnip.expand_or_jump()
                        else
                            fallback()
                        end
                    end, { 'i', 's' }),
                    ['<S-Tab>'] = cmp.mapping(function(fallback)
                        if cmp.visible() then
                            cmp.select_prev_item()
                        elseif luasnip.jumpable(-1) then
                            luasnip.jump(-1)
                        else
                            fallback()
                        end
                    end, { 'i', 's' }),
                }),
                sources = cmp.config.sources({
                    { name = 'nvim_lsp' },
                    { name = 'luasnip' },
                }, {
                        { name = 'buffer' },
                        { name = 'path' },
                    })
            })

            cmp.setup.cmdline({ '/', '?' }, {
                mapping = cmp.mapping.preset.cmdline(),
                sources = {
                    { name = 'buffer' }
                }
            })
        end
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
    },

    {
        'stevearc/oil.nvim',
        ---@module 'oil'
        ---@type oil.SetupOpts
        opts = {},
        -- Optional dependencies
        dependencies = { { "echasnovski/mini.icons", opts = {} } },
        -- dependencies = { "nvim-tree/nvim-web-devicons" }, -- use if prefer nvim-web-devicons
    },

    {
        "folke/snacks.nvim",
        priority = 1000,
        lazy = false,
        ---@type snacks.Config
        opts = {
            -- your configuration comes here
            -- or leave it empty to use the default settings
            -- refer to the configuration section below
            bigfile = { enabled = true },
            dashboard = { enabled = false },
            --dim = { enabled = true },
            indent = { enabled = true },
            notifier = { enabled = true },
            quickfile = { enabled = true },
            scope = { enabled = true },
            scroll = { enabled = true },
            terminal = { enabled = true },
            --statuscolumn = { enabled = true },
            --words = { enabled = true },
        },
    },

    {
        "olimorris/codecompanion.nvim",
        opts = {

            strategies = {
                chat = {
                    adapter = "openrouter_claude",
                },
                inline = {
                    adapter = "openrouter_claude",
                },
                cmd = {
                    adapter = "openrouter_claude",
                }
            },

            adapters = {
                openrouter_claude = function()
                    return require("codecompanion.adapters").extend("openai_compatible", {
                        env = {
                            url = "https://openrouter.ai/api",
                            api_key = os.getenv("OPENROUTER_API_KEY"),
                            chat_url = "/v1/chat/completions",
                            models_endpoint = "/v1/models",
                        },
                        schema = {
                            model = {
                                default = "anthropic/claude-3.7-sonnet",
                            },
                        },
                    })
                end,
            },

        },
        dependencies = {
            "nvim-lua/plenary.nvim",
            "nvim-treesitter/nvim-treesitter",
        },
    },

    {
        "MeanderingProgrammer/render-markdown.nvim",
        ft = { "markdown", "codecompanion" }
    },

    {
        "echasnovski/mini.diff",
        config = function()
            local diff = require("mini.diff")
            diff.setup({
                -- Disabled by default
                source = diff.gen_source.none(),
            })
        end,
    },

})
