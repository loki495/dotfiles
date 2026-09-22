local root = assert(vim.env.DOTFILES_ROOT, 'DOTFILES_ROOT is required')
vim.opt.runtimepath:prepend(root .. '/nvim')
local data = vim.fn.stdpath('data')
for _, plugin in ipairs({ 'phpactor.nvim', 'plenary.nvim' }) do
    vim.opt.runtimepath:append(data .. '/lazy/' .. plugin)
end

local prompts = {}
vim.ui.select = function(_, options, callback)
    table.insert(prompts, options.prompt)
    callback('No')
end
local function setup()
    package.loaded['phpactor'] = nil
    package.loaded['phpactor.config'] = nil
    package.loaded['phpactor.check_installed'] = nil
    dofile(root .. '/nvim/lua/plugins/phpactor.lua').config()
    local drained = false
    vim.schedule(function() drained = true end)
    assert(vim.wait(1000, function() return drained end), 'startup check did not run')
end

-- Exercise the actual installed plugin against the actual machine installation.
setup()
assert(#prompts == 0, 'existing PHPActor prompted for installation')
assert(vim.fn.executable(require('phpactor.config').options.install.bin) == 1)

local temp = vim.fn.tempname()
local original = { stdpath = vim.fn.stdpath, expand = vim.fn.expand, exepath = vim.fn.exepath }
local path_bin = ''
vim.fn.stdpath = function(kind)
    return kind == 'data' and temp .. '/data' or original.stdpath(kind)
end
vim.fn.expand = function(value)
    return value == '~/.local/bin/phpactor' and temp .. '/local/phpactor' or original.expand(value)
end
vim.fn.exepath = function(value)
    return value == 'phpactor' and path_bin or original.exepath(value)
end
local function executable(path)
    vim.fn.mkdir(vim.fn.fnamemodify(path, ':h'), 'p')
    vim.fn.writefile({ '#!/bin/sh', 'exit 0' }, path)
    assert(vim.fn.setfperm(path, 'rwxr-xr-x') == 1)
end
local function check(expected, missing)
    prompts = {}
    setup()
    local options = require('phpactor.config').options
    assert(options.install.bin == expected, vim.inspect(options.install))
    assert(options.lspconfig.enabled == false, 'duplicate LSP setup enabled')
    assert(#prompts == (missing and 1 or 0), vim.inspect(prompts))
    if missing then
        assert(prompts[1] == 'Phpactor is not installed, would you like to install it?')
        assert(expected == options.install.path .. 'phpactor/bin/phpactor', 'installer/check path mismatch')
    end
end
local managed = temp .. '/data/opt/phpactor/bin/phpactor'
check(managed, true)
executable(managed)
check(managed, false)
check(managed, false) -- Subsequent startup must still recognize a completed install.
path_bin = temp .. '/path/phpactor'
executable(path_bin)
check(path_bin, false)
local mason = temp .. '/data/mason/bin/phpactor'
executable(mason)
check(mason, false)
local local_bin = temp .. '/local/phpactor'
executable(local_bin)
check(local_bin, false)
vim.fn.setfperm(local_bin, 'rw-r--r--')
check(mason, false) -- Ignore a non-executable local copy.
vim.fn.delete(mason)
assert(vim.uv.fs_symlink(temp .. '/missing', mason))
check(path_bin, false) -- Ignore a broken Mason link.
for name, fn in pairs(original) do vim.fn[name] = fn end
vim.fn.delete(temp, 'rf')
print('PHPActor: live startup and 8 installation detection cases passed')
