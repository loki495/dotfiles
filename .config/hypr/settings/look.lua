-- General look and feel: general/decoration/animations/layouts/misc.
-- Consolidated from what used to be several small .conf files
-- (window_gaps, corners, blur_system, shadow_range, shadow_color,
-- border_size, border_color_active, border_color_inactive, layouts) --
-- kept as one hl.config() call per top-level section so there's no
-- ambiguity about whether separate calls deep-merge nested tables like
-- general.col across files.
-- See https://wiki.hypr.land/Configuring/Basics/Variables/

hl.config({
    general = {
        gaps_in = 10,
        gaps_out = 10,

        border_size = 1,

        col = {
            active_border = { colors = { "rgba(225,225,255,1)", "rgba(0,0,225,1)" }, angle = 45 },
            inactive_border = "rgba(0,0,0,1)",
        },

        layout = "dwindle",
    },

    decoration = {
        rounding = 15,

        blur = {
            enabled = true,
            size = 5,
            passes = 1,
        },

        shadow = {
            enabled = true,
            range = 30,
            render_power = 3,
            color = "rgba(0,0,0,1)",
        },
    },

    animations = {
        enabled = true,
    },
})

-- animations.conf
hl.curve("myBezier", { type = "bezier", points = { {0.05, 0.9}, {0.1, 1.05} } })

hl.animation({ leaf = "windows",    enabled = true, speed = 3, bezier = "myBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 3, bezier = "default", style = "popin 80%" })
hl.animation({ leaf = "border",     enabled = true, speed = 6, bezier = "default" })
hl.animation({ leaf = "fade",       enabled = true, speed = 3, bezier = "default" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 2, bezier = "default" })

-- See https://wiki.hypr.land/Configuring/Layouts/Dwindle-Layout/
hl.config({
    dwindle = {
        preserve_split = true,
    },
})

-- See https://wiki.hypr.land/Configuring/Layouts/Master-Layout/
hl.config({
    master = {
        new_status = "master",
    },
})

hl.config({
    misc = {
        disable_hyprland_logo = true,
        font_family = "JetBrains Mono",
    },
})
