return {
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

        -- Rust setup (move your rust-analyzer.lua contents here for simplicity)
        require('lspconfig').rust_analyzer.setup({
            capabilities = capabilities,
            settings = {
                ["rust-analyzer"] = {
                    cargo = { allFeatures = true },
                    procMacro = { enable = true },
                    inlayHints = {
                        bindingModeHints = { enable = true },
                        chainingHints = { enable = true },
                        parameterHints = { enable = true },
                        typeHints = { enable = true },
                    },
                },
            },
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
}
