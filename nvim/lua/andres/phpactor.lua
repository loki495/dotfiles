local M = {}

function M.bin()
    local data = vim.fn.stdpath('data')
    local managed = data .. '/opt/phpactor/bin/phpactor'
    -- Explicit paths keep detection independent of Mason's PATH setup order.
    for _, candidate in ipairs({
        vim.fn.expand('~/.local/bin/phpactor'),
        data .. '/mason/bin/phpactor',
        vim.fn.exepath('phpactor'),
        managed,
    }) do
        if candidate ~= '' and vim.fn.executable(candidate) == 1 then
            return candidate
        end
    end
    -- A fresh install must be checked where phpactor.nvim actually installs it.
    return managed
end

return M
