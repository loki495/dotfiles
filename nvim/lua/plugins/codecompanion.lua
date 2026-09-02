return {
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

        context = {
            -- Include more project-wide information
            sources = {
                "buffers",       -- open buffers
                "lsp",           -- LSP symbols (functions, classes)
                "git",           -- staged/tracked files
                "cwd",           -- contents of current working directory
            },
            -- Limit to avoid overloading token usage
            cwd = {
                include = { "%.php$", "%.js$", "%.css$" },
                --max_files = 20,
                max_file_size = 100000, -- bytes
            },
        },
    },
    dependencies = {
        "nvim-lua/plenary.nvim",
    },
}
