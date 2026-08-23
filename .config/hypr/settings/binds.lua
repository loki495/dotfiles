-- Keybindings.
-- See https://wiki.hypr.land/Configuring/Basics/Binds/
-- and https://wiki.hypr.land/Configuring/Basics/Dispatchers/

local mainMod = "SUPER"

hl.bind(mainMod .. " + SHIFT + G", hl.dsp.exec_cmd("footclient -e ~/.local/bin/bear/implement_gum.sh disable"))

-- Wallpaper daemon restart (from background.conf)
hl.bind(mainMod .. " + SHIFT + C", hl.dsp.exec_cmd("killall -9 wpaperd && wpaperd"))

-- Clipboard manager
hl.bind("SUPER + V", hl.dsp.exec_cmd("cliphist list | wofi --dmenu | cliphist decode | wl-copy"))

-- Install Garuda Hyprland
hl.bind(mainMod .. " + I", hl.dsp.exec_cmd(".local/bin/calamares.sh"))

hl.bind(mainMod .. " + SHIFT + R", hl.dsp.exec_cmd("hyprctl reload"))
hl.bind(mainMod .. " + code:36", hl.dsp.exec_cmd("footclient -D ~"))
hl.bind(mainMod .. " + SHIFT + Q", hl.dsp.window.close())
hl.bind(mainMod .. " + SHIFT + E", hl.dsp.exec_cmd("nwgbar"))
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd("thunar"))
hl.bind(mainMod .. " + Y", hl.dsp.window.float())
hl.bind("SUPER + D", hl.dsp.exec_cmd("pkill wofi || wofi --normal-window --show drun --allow-images"), { release = true })
hl.bind(mainMod .. " + SHIFT + D", hl.dsp.exec_cmd("nwg-drawer -mb 10 -mr 10 -ml 10 -mt 10"))
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo())
-- hl.bind(mainMod .. " + SHIFT + P", hl.dsp.layout("togglesplit")) -- dwindle (was commented out originally)
-- hl.bind(mainMod .. " + Z", hl.dsp.exec_cmd("/usr/bin/python /usr/bin/zim")) -- (was commented out originally)

-- Mainmod + Function keys
hl.bind(mainMod .. " + F1",  hl.dsp.exec_cmd("firedragon"))
hl.bind(mainMod .. " + F2",  hl.dsp.exec_cmd("thunderbird"))
hl.bind(mainMod .. " + F3",  hl.dsp.exec_cmd("thunar"))
hl.bind(mainMod .. " + F4",  hl.dsp.exec_cmd("geany"))
hl.bind(mainMod .. " + F5",  hl.dsp.exec_cmd("github-desktop"))
hl.bind(mainMod .. " + F6",  hl.dsp.exec_cmd("gparted"))
hl.bind(mainMod .. " + F7",  hl.dsp.exec_cmd("inkscape"))
hl.bind(mainMod .. " + F8",  hl.dsp.exec_cmd("blender"))
hl.bind(mainMod .. " + F9",  hl.dsp.exec_cmd("meld"))
hl.bind(mainMod .. " + F10", hl.dsp.exec_cmd("joplin-desktop"))
hl.bind(mainMod .. " + F11", hl.dsp.exec_cmd("snapper-tools"))
hl.bind(mainMod .. " + F12", hl.dsp.exec_cmd("galculator"))

-- Move focus with mainMod + arrow keys
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "l" }))
hl.bind(mainMod .. " + H",     hl.dsp.focus({ direction = "l" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "r" }))
hl.bind(mainMod .. " + L",     hl.dsp.focus({ direction = "r" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "u" }))
hl.bind(mainMod .. " + K",     hl.dsp.focus({ direction = "u" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "d" }))
hl.bind(mainMod .. " + J",     hl.dsp.focus({ direction = "d" }))

-- Cycle input focus to the other monitor (no-op if only one is connected)
hl.bind(mainMod .. " + TAB", hl.dsp.focus({ monitor = "+1" }))

-- Switch workspaces with mainMod + [0-9] - forces the workspace onto whichever
-- monitor is currently focused, instead of just refocusing wherever it already is.
-- Move to workspace with focused container with ALT + SHIFT + [0-9]
-- Move active window to a workspace with mainMod + SHIFT + [0-9]
for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    hl.bind(mainMod .. " + " .. key,         hl.dsp.focus({ workspace = i, on_current_monitor = true }))
    hl.bind("ALT + SHIFT + " .. key,         hl.dsp.window.move({ workspace = i, follow = true }))
    hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i, follow = false }))
end

-- Scroll through existing workspaces with mainMod + scroll
hl.bind(mainMod .. " + bracketleft",  hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mainMod .. " + bracketright", hl.dsp.focus({ workspace = "e+1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- set volume (laptops only and may or may not work on PCs)
hl.bind("code:122", hl.dsp.exec_cmd([[pamixer --decrease 5; notify-send " Volume: "$(pamixer --get-volume) -t 500]]))
hl.bind("code:123", hl.dsp.exec_cmd([[pamixer --increase 5; notify-send " Volume: "$(pamixer --get-volume) -t 500]]))
hl.bind("code:121", hl.dsp.exec_cmd([[pamixer --toggle-mute; notify-send " Volume: Toggle-mute" -t 500]]))
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd([[pactl set-source-mute @DEFAULT_SOURCE@ toggle; notify-send "System Mic: Toggle-mute" -t 500]]))

-- other bindings
hl.bind(mainMod .. " + O", hl.dsp.exec_cmd("firedragon"))
hl.bind(mainMod .. " + M", hl.dsp.window.fullscreen({ mode = "maximized" }))
hl.bind(mainMod .. " + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }))
hl.bind(mainMod .. " + SHIFT + F", hl.dsp.window.fullscreen_state({ internal = 0, client = 2 }))
hl.bind("code:232", hl.dsp.exec_cmd("brightnessctl -c backlight set 5%-"))
hl.bind("code:233", hl.dsp.exec_cmd("brightnessctl -c backlight set +5%"))

-- for resizing window: switch to a submap called resize
hl.bind(mainMod .. " + R", hl.dsp.submap("resize"))

hl.define_submap("resize", function()
    -- sets repeatable binds for resizing the active window
    hl.bind("right", hl.dsp.window.resize({ x = 50, y = 0, relative = true }))
    hl.bind("L",     hl.dsp.window.resize({ x = 50, y = 0, relative = true }))
    hl.bind("left",  hl.dsp.window.resize({ x = -50, y = 0, relative = true }))
    hl.bind("H",     hl.dsp.window.resize({ x = -50, y = 0, relative = true }))
    hl.bind("up",    hl.dsp.window.resize({ x = 0, y = -50, relative = true }))
    hl.bind("K",     hl.dsp.window.resize({ x = 0, y = -50, relative = true }))
    hl.bind("down",  hl.dsp.window.resize({ x = 0, y = 50, relative = true }))
    hl.bind("J",     hl.dsp.window.resize({ x = 0, y = 50, relative = true }))

    -- use reset to go back to the global submap
    hl.bind("escape", hl.dsp.submap("reset"))
end)

-- to move window
hl.bind(mainMod .. " + SHIFT + up",    hl.dsp.window.move({ direction = "u" }))
hl.bind(mainMod .. " + SHIFT + K",     hl.dsp.window.move({ direction = "u" }))
hl.bind(mainMod .. " + SHIFT + down",  hl.dsp.window.move({ direction = "d" }))
hl.bind(mainMod .. " + SHIFT + J",     hl.dsp.window.move({ direction = "d" }))
hl.bind(mainMod .. " + SHIFT + left",  hl.dsp.window.move({ direction = "l" }))
hl.bind(mainMod .. " + SHIFT + H",     hl.dsp.window.move({ direction = "l" }))
hl.bind(mainMod .. " + SHIFT + right", hl.dsp.window.move({ direction = "r" }))
hl.bind(mainMod .. " + SHIFT + L",     hl.dsp.window.move({ direction = "r" }))

-- video play/pause bindings
hl.bind("code:172", hl.dsp.exec_cmd("playerctl play-pause"))
hl.bind("code:171", hl.dsp.exec_cmd("playerctl next"))
hl.bind("code:173", hl.dsp.exec_cmd("playerctl previous"))

-- screenshot
-- Screenshot a window (note: shares mainMod+M with the maximize bind above;
-- both fire in order, same as the original hyprlang config did)
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd("hyprshot -m window"))
-- Screenshot a region
hl.bind(mainMod .. " + SHIFT + M", hl.dsp.exec_cmd("hyprshot -m region --freeze"))
hl.bind(mainMod .. " + SHIFT + ALT + M", hl.dsp.exec_cmd("hyprshot -m region --freeze --clipboard-only"))

hl.bind("Print", hl.dsp.exec_cmd("grimblast save screen && notify-send Screenshot captured"))
hl.bind("SHIFT + Print", hl.dsp.exec_cmd([[grimblast save area && notify-send Selected\ area captured]]))
hl.bind("ALT + Print", hl.dsp.exec_cmd([[grimblast save active && notify-send Active\ window captured]]))
hl.bind("ALT + SHIFT + Print", hl.dsp.exec_cmd([[grimblast output active && notify-send Output captured]]))

hl.bind("ALT + SHIFT + H", hl.dsp.exec_cmd("~/.config/hypr/scripts/nwg_dock_toggle.sh"))

-- Special workspace (scratchpad) -- preserved exactly as originally written,
-- including the repeated/redundant-looking toggle+move sequence.
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("magic"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "+0", follow = true }))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("magic"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic", follow = true }))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.workspace.toggle_special("magic"))

-- Footclient window group cycling
hl.bind(mainMod .. " + x",         hl.dsp.group.next())
hl.bind(mainMod .. " + apostrophe", hl.dsp.group.next())
hl.bind(mainMod .. " + z",         hl.dsp.group.prev())
hl.bind(mainMod .. " + semicolon", hl.dsp.group.prev())
hl.bind(mainMod .. " + SHIFT + x",         hl.dsp.group.move_window({ forward = true }))
hl.bind(mainMod .. " + SHIFT + apostrophe", hl.dsp.group.move_window({ forward = true }))
hl.bind(mainMod .. " + SHIFT + z",         hl.dsp.group.move_window({ forward = false }))
hl.bind(mainMod .. " + SHIFT + semicolon", hl.dsp.group.move_window({ forward = false }))

hl.bind(mainMod .. " + n", hl.dsp.workspace.toggle_special("scratchpad"))
