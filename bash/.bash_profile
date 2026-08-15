#
# ~/.bash_profile
#

[[ -f ~/.bashrc ]] && . ~/.bashrc


# Added by Antigravity CLI installer
export PATH="/home/andres/.local/bin:$PATH"

# Auto-launch Hyprland on the tty1 console autologin only -- never over SSH
# or any other pty. Using exec (not just running it) means when Hyprland
# exits/is killed, this login shell exits too, which lets getty@tty1's
# Restart=always cycle a fresh autologin + relaunch automatically, instead
# of needing a manual restart.
if [ -z "$WAYLAND_DISPLAY" ] && [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec start-hyprland
fi
