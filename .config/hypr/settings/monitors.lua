-- Monitor configuration.
-- See https://wiki.hypr.land/Configuring/Basics/Monitors/

-- Laptop panel, kept at native res/scale.
hl.monitor({ output = "eDP-1", mode = "1920x1080@60", position = "0x0", scale = 1 })

-- TV over HDMI, extended to the right, scaled up for readability from the couch.
hl.monitor({ output = "HDMI-A-1", mode = "3840x2160@59.94", position = "1920x0", scale = 3 })
