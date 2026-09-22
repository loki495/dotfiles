local root = assert(vim.env.DOTFILES_ROOT, 'Set DOTFILES_ROOT')
vim.opt.rtp:prepend(root .. '/nvim')
vim.cmd('filetype on')
vim.cmd('syntax enable')
require('andres.highlighting').setup()
local cases = {
    { 'test.sh', 'sh', 'bash', { {'bash', 'name'}, {'html', 'strong'} } },
    { 'test.php', 'php', 'php', { {'php', 'return'}, {'php', '$x'}, {'html', 'section'}, {'javascript', 'const'}, {'json', 'title'} } },
    { 'test.js', 'javascript', 'javascript', { {'javascript', 'const'}, {'javascript', 'section'}, {'javascript', 'name'} } },
    { 'test.blade.php', 'php', 'blade', { {'blade', '@if'}, {'blade', 'div'}, {'php_only', '$user'}, {'javascript', 'const'}, {'css', 'color'} } },
    { 'test.md', 'markdown', 'markdown', { {'markdown', '#'}, {'markdown_inline', 'bold'}, {'bash', 'printf'}, {'php', '$name'}, {'javascript', 'const'}, {'blade', '@if'} } },
}
for _, case in ipairs(cases) do
    vim.cmd.edit(vim.fn.fnameescape(root .. '/scripts/ci/fixtures/' .. case[1]))
    local buf = vim.api.nvim_get_current_buf()
    assert(vim.bo.filetype == case[2], case[1] .. ': incorrect filetype ' .. vim.bo.filetype)
    assert(vim.treesitter.highlighter.active[buf], case[1] .. ': inactive highlighter')
    local parser = assert(vim.treesitter.get_parser(buf, case[3]))
    parser:parse(true)
    local captures = {}
    parser:for_each_tree(function(tree, language_tree)
        local lang = language_tree:lang()
        local query = vim.treesitter.query.get(lang, 'highlights')
        if not query then return end
        for id, node in query:iter_captures(tree:root(), buf, 0, -1) do
            local text = vim.treesitter.get_node_text(node, buf)
            table.insert(captures, { lang, text, query.captures[id] })
        end
    end)
    for _, expected in ipairs(case[4]) do
        local found = false
        for _, capture in ipairs(captures) do
            if capture[1] == expected[1] and capture[2]:find(expected[2], 1, true) then found = true end
        end
        assert(found, case[1] .. ': missing capture ' .. vim.inspect(expected) .. '\n' .. vim.inspect(captures))
    end
    print('PASS native captures: ' .. case[1])
end
-- Failures must preserve editing, expose diagnostics, and retain regex fallback.
local original_parser = vim.treesitter.get_parser
local original_query = vim.treesitter.query.get
local notifications = {}
vim.notify = function(message) table.insert(notifications, message) end
for _, mode in ipairs({ 'missing parser', 'invalid query' }) do
    vim.cmd.enew()
    local buf = vim.api.nvim_get_current_buf()
    vim.bo.filetype = ''
    vim.treesitter.get_parser = mode == 'missing parser' and function() return nil end or function() return {} end
    vim.treesitter.query.get = mode == 'invalid query' and function() error('fixture invalid query') end or original_query
    vim.bo.filetype = mode == 'missing parser' and 'sh' or 'php'
    assert(not vim.treesitter.highlighter.active[buf], mode .. ': unexpected highlighter')
    assert(vim.bo.syntax == vim.bo.filetype, mode .. ': missing fallback')
end
vim.treesitter.get_parser = original_parser
vim.treesitter.query.get = original_query
vim.wait(100, function() return #notifications == 2 end)
assert(#notifications == 2, 'Expected diagnostic for both failures')
assert(notifications[1]:find('parser unavailable', 1, true))
assert(notifications[2]:find('fixture invalid query', 1, true), vim.inspect(notifications))
print('PASS missing-parser and invalid-query fallback diagnostics')
