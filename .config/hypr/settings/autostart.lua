-- Autostart.
-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

hl.on("hyprland.start", function()
    hl.exec_cmd("waybar")
    -- Feeds instant refresh signals to waybar's custom/ws-* workspace
    -- buttons (stand-in for the broken hyprland/workspaces click handler,
    -- see waybar config comments). Remove once waybar ships a fix.
    hl.exec_cmd("~/.config/waybar/scripts/workspace-watcher.sh")
    hl.exec_cmd("wpaperd")

    hl.exec_cmd("nm-applet --indicator")
    hl.exec_cmd("mako") -- notifications
    hl.exec_cmd("/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1")

    hl.exec_cmd("foot --server")

    hl.exec_cmd("xrdb -load ~/.Xresources")

    -- Clipboard manager
    hl.exec_cmd("wl-paste --type text --watch cliphist store")  -- Stores only text data
    hl.exec_cmd("wl-paste --type image --watch cliphist store") -- Stores only image data

    -- Use gtk-settings
    hl.exec_cmd("apply-gsettings")

    hl.exec_cmd("hypridle")

    -- Note: original hyprlang used a "[silent]" exec-once flag on these two
    -- (suppresses stdout/stderr logging only, no functional difference) --
    -- no confirmed Lua equivalent found, so just running them as normal.
    hl.exec_cmd([[bash -c "sleep 0.6; footclient" &]])
    hl.exec_cmd([[bash -c "sleep 1; brave" &]])
end)
