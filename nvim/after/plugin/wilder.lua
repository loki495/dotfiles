local wilder = require('wilder')
wilder.setup({modes = {':', '/', '?'}})

wilder.set_option('renderer', wilder.popupmenu_renderer(
  wilder.popupmenu_palette_theme({
    -- 'single', 'double', 'rounded' or 'solid'
    -- can also be a list of 8 characters, see :h wilder#popupmenu_palette_theme() for more details
    border = 'rounded',
    max_height = '75%',      -- max height of the palette
    min_height = 0,          -- set to the same as 'max_height' for a fixed height window
    prompt_position = 'top', -- 'top' or 'bottom' to set the location of the prompt
    reverse = 0,             -- set to 1 to reverse the order of the list, use in combination with 'prompt_position'
    highlighter = {
      -- wilder.lua_pcre2_highlighter(), -- requires `luarocks install pcre2`
      wilder.lua_fzy_highlighter(),   -- requires fzy-lua-native vim plugin found
       -- at https://github.com/romgrk/fzy-lua-native
    },
    highlights = {
      accent = wilder.make_hl('WilderAccent', 'Pmenu', {{a = 1}, {a = 1}, {foreground = '#f4468f'}}),
      selected_accent = wilder.make_hl('WilderSelectedAccent', 'PmenuSel', {{a = 1}, {a = 1}, {foreground = '#ff6b9d'}}),
      default = wilder.make_hl('WilderDefault', 'Pmenu', {{}, {}, {}}),
      selected = wilder.make_hl('WilderSelected', 'PmenuSel', {{}, {}, {}}),
    },
  })
))

wilder.set_option('pipeline', {
  wilder.branch(
    wilder.python_search_pipeline({
      pattern = 'fuzzy',
    }),
    wilder.cmdline_pipeline({
      fuzzy = 1,
      fuzzy_filter = wilder.lua_fzy_filter(),
      -- set_pcre2_pattern = 1,
    })
  ),
})

--wilder.set_option('renderer', wilder.renderer_mux({
  --[':'] = wilder.popupmenu_renderer({
    --highlighter = highlighters,
  --}),
  --['/'] = wilder.wildmenu_renderer({
    --highlighter = highlighters,
  --}),
--}))
