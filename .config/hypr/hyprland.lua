-- Hyprland Lua config. Migrated from the old hyprlang (.conf) format ahead
-- of its removal in Hyprland 0.57. See https://wiki.hypr.land/Configuring/Start/
--
-- Split across settings/*.lua modules, same idea as the old settings/*.conf
-- split, but consolidated where multiple old files targeted the same
-- hl.config() top-level section (see settings/look.lua for why).

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

-- NVIDIA dGPU (card1) primary - avoids cross-GPU frame copy for the TV (HDMI-A-1),
-- which is wired to it. Intel iGPU (card2) still listed since eDP-1 (laptop panel)
-- needs it available as a fallback. Trades battery life/heat for lower latency.
hl.env("AQ_DRM_DEVICES", "/dev/dri/card1:/dev/dri/card2")

-- Forces linear (no-modifier) DRM buffers everywhere. Without this, eDP-1's
-- cross-GPU blit (NVIDIA-rendered frame -> Intel, since eDP-1 is wired to the
-- iGPU) intermittently fails with EGL_BAD_MATCH on eglCreateImageKHR when the
-- two GPUs negotiate incompatible tiling/compression modifiers (caught live:
-- Intel side allocated Y_TILED_CCS, import from the NVIDIA source failed) --
-- this was the confirmed cause of the panel going black-but-backlit and
-- unresponsive after DPMS/suspend/VT-switch resume. Linear buffers are a
-- format both GPUs always agree on. Costs some memory bandwidth; negligible
-- for a 2D compositor.
hl.env("AQ_NO_MODIFIERS", "1")

hl.env("XDG_CURRENT_DESKTOP", "Hyprland")

------------------
---- MONITORS ----
------------------

require("settings.monitors")

-----------------------
---- LOOK AND FEEL ----
-----------------------

require("settings.look")

---------------
---- INPUT ----
---------------

require("settings.input")

---------------------
---- KEYBINDINGS ----
---------------------

require("settings.binds")

--------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------

require("settings.rules")

-------------------
---- AUTOSTART ----
-------------------

require("settings.autostart")
