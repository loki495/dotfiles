-- Cursor, keyboard/touchpad input, per-device overrides.

-- Software cursor, not hardware. Hit a hardware-cursor-plane corruption bug
-- (frozen cursor, magenta/green flashing artifacts, eventually a full
-- compositor hang) triggered by toggling DPMS on eDP-1. Matches two known
-- upstream issues on hybrid-GPU setups: Hyprland/Aquamarine hardware cursor
-- desync on a secondary output (hyprwm/Hyprland#13449, fixed by this same
-- setting) and an NVIDIA 580.x driver bug where cursor-shape-change artifacts
-- aren't cleared (forums.developer.nvidia.com, driver 580.105.08 thread; this
-- machine runs 580.173.02, same branch). The docs describe this as a
-- preventive setting applied before the desync happens, not a live fix once
-- already corrupted -- confirmed here too, toggling it live mid-hang didn't
-- recover the screen.
hl.config({
    cursor = {
        no_hardware_cursors = true,
    },

    input = {
        kb_layout = "us",
        kb_variant = "",
        kb_model = "",
        kb_options = "",
        kb_rules = "",
        numlock_by_default = true,
        follow_mouse = 1,

        touchpad = {
            natural_scroll = false,
            tap_to_click = true,
            disable_while_typing = true,
        },

        sensitivity = 0, -- -1.0 - 1.0, 0 means no modification.
    },
})

-- Example per-device config
-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/
hl.device({
    name = "yichip-wireless-device-consumer-control-1",
    sensitivity = 1.0,
})
hl.device({
    name = "yichip-wireless-device-mouse",
    sensitivity = 1.0,
})
