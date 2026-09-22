-- Tailwind Tools uses a Node remote plugin; keep its host user-local.
local node_host = vim.fn.expand("~/.local/share/nvim/node-provider/node_modules/.bin/neovim-node-host")
if vim.fn.executable(node_host) == 1 then
    vim.g.node_host_prog = node_host
end
