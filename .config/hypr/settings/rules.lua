-- Window rules, layer rules, workspace rules, window grouping.
-- See https://wiki.hypr.land/Configuring/Basics/Window-Rules/
-- and https://wiki.hypr.land/Configuring/Basics/Workspace-Rules/

-- Layer blur (old "blurls" shorthand -> layer rules)
hl.layer_rule({ match = { namespace = "wofi" }, blur = true })
hl.layer_rule({ match = { namespace = "thunar" }, blur = true })
hl.layer_rule({ match = { namespace = "gedit" }, blur = true })
hl.layer_rule({ match = { namespace = "gtk-layer-shell" }, blur = true }) -- for nwg-drawer
hl.layer_rule({ match = { namespace = "catfish" }, blur = true })
-- hl.layer_rule({ match = { namespace = "nwg-dock" }, blur = true }) -- (was commented out originally)

-- waybar (from status_bar.conf)
hl.layer_rule({ match = { namespace = "waybar" }, blur = true, ignore_alpha = 0.0 })

-- Explicit blur+ignore_alpha for gtk-layer-shell, in addition to the plain
-- blurls-equivalent rule above -- both existed in the original config.
hl.layer_rule({ match = { namespace = "gtk-layer-shell" }, blur = true, ignore_alpha = 0.0 })

-- Window opacity
hl.window_rule({ match = { class = "thunar" }, opacity = "0.85" })
hl.window_rule({ match = { class = "footclient" }, opacity = "0.85" })
hl.window_rule({ match = { class = "catfish" }, opacity = "0.85" })
hl.window_rule({ match = { class = "nvim" }, opacity = "0.85" })

-- window rules with evaluation
hl.window_rule({ match = { float = true }, opacity = "0.85 0.85" })

hl.window_rule({ match = { class = "wofi" }, stay_focused = true })

-- if someone wants it by heart, but you can edit the picture with all the
-- features in gweenview (KDE image viewer) just same as flameshot
hl.window_rule({ match = { title = "^(flameshot)$" }, move = { 0, 0 } })

hl.window_rule({ match = { class = "garuda-assistant" }, float = true })
hl.window_rule({ match = { class = "garuda-boot-options" }, float = true })
hl.window_rule({ match = { class = "garuda-gamer" }, float = true })
hl.window_rule({ match = { class = "garuda-network-assistant" }, float = true })
hl.window_rule({ match = { class = "garuda-settings-manager" }, float = true })
hl.window_rule({ match = { class = "garuda-welcome" }, float = true })

hl.window_rule({ match = { class = "^(trillian)$" }, workspace = "1" })
hl.window_rule({ match = { class = "^(brave-browser)$" }, workspace = "2" })
hl.window_rule({ match = { class = "^(footclient)$" }, workspace = "3" })
hl.window_rule({ match = { class = "^(steam)$" }, workspace = "9" })
hl.window_rule({ match = { class = "^(zim)" }, float = true })
hl.window_rule({ match = { class = "^(zim)$" }, size = { 800, 600 } })

hl.workspace_rule({ workspace = "1", layout = "dwindle" })

-- Footclient windows - full size, tabbed/grouped
hl.window_rule({
    name = "footclient group",
    match = { class = "^footclient$" },
    group = "set lock invade",
})

hl.window_rule({ match = { title = "^(Sysinfo.*)$" }, float = true })
hl.window_rule({ match = { title = "^(Sysinfo.*)$" }, move = { 1400, 55 } })

-- $scratchpad = nvimfloat
hl.window_rule({ match = { class = "^(nvimfloat)$" }, float = true })
hl.window_rule({ match = { class = "^(nvimfloat).*" }, fullscreen_state = "1 1" })
hl.window_rule({ match = { class = "^(nvimfloat)$" }, workspace = "special:scratchpad" })

-- group:groupbar
hl.config({
    group = {
        groupbar = {
            enabled = true,
            gradients = true,
            render_titles = true,
            font_size = 16,
            font_family = "JetBrains Mono",
            font_weight_active = "bold",
            font_weight_inactive = "normal",
            height = 25,
            col = {
                locked_active = "0x99638aff",
                locked_inactive = "0x22638aff",
            },
            gaps_in = 5,
            gradient_rounding = 10,
            indicator_height = 0,
            indicator_gap = 5,
        },
    },
})
