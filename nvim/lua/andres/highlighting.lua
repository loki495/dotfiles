local M = {}
local languages = {
    sh = "bash", bash = "bash", markdown = "markdown", blade = "blade",
    html = "html", css = "css", yaml = "yaml", javascript = "javascript",
    javascriptreact = "javascript", typescript = "typescript", typescriptreact = "tsx",
    vue = "vue", json = "json", php = "php", rust = "rust", toml = "toml",
}
local warned = {}

function M.start(buf)
    local ft = vim.bo[buf].filetype
    local lang = languages[ft]
    if not lang then return end
    -- Keep PHP filetype/LSP behavior while parsing Blade templates correctly.
    if ft == "php" and vim.api.nvim_buf_get_name(buf):match("%.blade%.php$") then
        lang = "blade"
    end
    local ok, err = pcall(function()
        local parser = vim.treesitter.get_parser(buf, lang)
        if not parser then error("parser unavailable: " .. lang) end
        local query = vim.treesitter.query.get(lang, "highlights")
        if not query or #query.captures == 0 then error("highlight queries unavailable: " .. lang) end
        vim.treesitter.start(buf, lang)
        if not vim.treesitter.highlighter.active[buf] then error("highlighter did not attach: " .. lang) end
        parser:parse(true)
    end)
    if not ok then
        vim.treesitter.stop(buf)
        vim.bo[buf].syntax = ft
        if not warned[lang] then
            warned[lang] = true
            vim.schedule(function()
                vim.notify("Native highlighting for " .. lang .. " unavailable: " .. tostring(err)
                    .. "\nRun install_neovim.sh --parsers and --queries; using syntax fallback.", vim.log.levels.WARN)
            end)
        end
    end
    return ok
end

local function query_directives()
    local query = vim.treesitter.query
    local available = query.list_directives()
    if not vim.tbl_contains(available, "downcase!") then
        query.add_directive("downcase!", function(match, _, buf, predicate, metadata)
            local id = predicate[2]
            local node = (match[id] or {})[1]
            if not node then return end
            local text = vim.treesitter.get_node_text(node, buf, { metadata = metadata[id] })
            metadata[id] = metadata[id] or {}
            metadata[id].text = text:lower()
        end)
    end
    if not vim.tbl_contains(available, "set-lang-from-mimetype!") then
        query.add_directive("set-lang-from-mimetype!", function(match, _, buf, predicate, metadata)
            local node = (match[predicate[2]] or {})[1]
            if not node then return end
            local mime = vim.treesitter.get_node_text(node, buf):lower()
            local types = {
                ["text/javascript"] = "javascript", ["application/javascript"] = "javascript",
                ["text/ecmascript"] = "javascript", ["application/ecmascript"] = "javascript",
                ["module"] = "javascript", ["application/ld+json"] = "json",
            }
            metadata["injection.language"] = types[mime] or mime:match("([^/]+)$")
        end)
    end
end

function M.setup()
    query_directives()
    vim.filetype.add({ pattern = { [".*%.blade%.php"] = { "php", { priority = 10 } } } })
    vim.treesitter.language.register("bash", { "sh", "bash" })
    vim.treesitter.language.register("javascript", { "javascript", "javascriptreact", "js" })
    local group = vim.api.nvim_create_augroup("AndresHighlighting", { clear = true })
    vim.api.nvim_create_autocmd("FileType", {
        group = group,
        callback = function(args) M.start(args.buf) end,
    })
end

return M
