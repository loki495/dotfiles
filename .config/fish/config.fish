## Set values
# Hide welcome message & ensure we are reporting fish as shell
set fish_greeting
set VIRTUAL_ENV_DISABLE_PROMPT "1"
set -x SHELL /usr/bin/fish

# Use bat for man pages
set -xU MANPAGER "sh -c 'col -bx | bat -l man -p'"
set -xU MANROFFOPT "-c"

# Hint to exit PKGBUILD review in Paru
set -x PARU_PAGER "less -P \"Press 'q' to exit the PKGBUILD review.\""

## Export variable need for qt-theme
if type "qtile" >> /dev/null 2>&1
   set -x QT_QPA_PLATFORMTHEME "qt5ct"
end

# Set settings for https://github.com/franciscolourenco/done
set -U __done_min_cmd_duration 10000
set -U __done_notification_urgency_level low

## Environment setup
# Apply .profile: use this to put fish compatible .profile stuff in
if test -f ~/.fish_profile
  source ~/.fish_profile
end

# Add ~/.local/bin to PATH
if test -d ~/.local/bin
    if not contains -- ~/.local/bin $PATH
        set -p PATH ~/.local/bin
    end
end

# Add depot_tools to PATH
if test -d ~/Applications/depot_tools
    if not contains -- ~/Applications/depot_tools $PATH
        set -p PATH ~/Applications/depot_tools
    end
end

## Starship prompt
if status --is-interactive
   source ("/usr/bin/starship" init fish --print-full-init | psub)
end

## Advanced command-not-found hook
if test -f /usr/share/doc/find-the-command/ftc.fish
    source /usr/share/doc/find-the-command/ftc.fish
end

## Functions
# Functions needed for !! and !$ https://github.com/oh-my-fish/plugin-bang-bang
function __history_previous_command
  switch (commandline -t)
  case "!"
    commandline -t $history[1]; commandline -f repaint
  case "*"
    commandline -i !
  end
end

function __history_previous_command_arguments
  switch (commandline -t)
  case "!"
    commandline -t ""
    commandline -f history-token-search-backward
  case "*"
    commandline -i '$'
  end
end

if [ "$fish_key_bindings" = fish_vi_key_bindings ];
  bind -Minsert ! __history_previous_command
  bind -Minsert '$' __history_previous_command_arguments
else
  bind ! __history_previous_command
  bind '$' __history_previous_command_arguments
end

# Fish command history
function history
    builtin history --show-time='%F %T '
end

function backup --argument filename
    cp $filename $filename.bak
end

# Copy DIR1 DIR2
function copy
    set count (count $argv | tr -d \n)
    if test "$count" = 2; and test -d "$argv[1]"
	set from (echo $argv[1] | string trim --right --chars=/)
	set to (echo $argv[2])
        command cp -r $from $to
    else
        command cp $argv
    end
end

# Cleanup local orphaned packages
function cleanup
    while pacman -Qdtq
        sudo pacman -R (pacman -Qdtq)
        if test "$status" -eq 1
           break
        end
    end
end

## Useful aliases

# Replace ls with eza
alias ls 'eza -al --color=always --group-directories-first --icons' # preferred listing
alias lsz 'eza -al --color=always --total-size --group-directories-first --icons' # include file size
alias la 'eza -a --color=always --group-directories-first --icons'  # all files and dirs
alias ll 'eza -l --color=always --group-directories-first --icons'  # long format
alias lt 'eza -aT --color=always --group-directories-first --icons' # tree listing
alias l. 'eza -ald --color=always --group-directories-first --icons .*' # show only dotfiles

# Replace some more things with better alternatives
# alias cat 'bat --style header --style snip --style changes --style header'
if not test -x /usr/bin/yay; and test -x /usr/bin/paru
    alias yay 'paru'
end


# Common use
alias .. 'cd ..'
alias ... 'cd ../..'
alias .... 'cd ../../..'
alias ..... 'cd ../../../..'
alias ...... 'cd ../../../../..'
alias big 'expac -H M "%m\t%n" | sort -h | nl'     # Sort installed packages according to size in MB (expac must be installed)
alias dir 'dir --color=auto'
alias fixpacman 'sudo rm /var/lib/pacman/db.lck'
alias gitpkg 'pacman -Q | grep -i "\-git" | wc -l' # List amount of -git packages
alias grep 'ugrep --color=auto'
alias egrep 'ugrep -E --color=auto'
alias fgrep 'ugrep -F --color=auto'
alias grubup 'sudo update-grub'
alias hw 'hwinfo --short'                          # Hardware Info
alias ip 'ip -color'
alias psmem 'ps auxf | sort -nr -k 4'
alias psmem10 'ps auxf | sort -nr -k 4 | head -10'
alias rmpkg 'sudo pacman -Rdd'
alias tarnow 'tar -acf '
alias untar 'tar -zxvf '
alias upd '/usr/bin/garuda-update'
alias vdir 'vdir --color=auto'
alias wget 'wget -c '

# Get fastest mirrors
alias mirror 'sudo reflector -f 30 -l 30 --number 10 --verbose --save /etc/pacman.d/mirrorlist'
alias mirrora 'sudo reflector --latest 50 --number 20 --sort age --save /etc/pacman.d/mirrorlist'
alias mirrord 'sudo reflector --latest 50 --number 20 --sort delay --save /etc/pacman.d/mirrorlist'
alias mirrors 'sudo reflector --latest 50 --number 20 --sort score --save /etc/pacman.d/mirrorlist'

# Help people new to Arch
alias apt 'man pacman'
alias apt-get 'man pacman'
alias please 'sudo'
alias tb 'nc termbin.com 9999'
alias helpme 'echo "To print basic information about a command use tldr <command>"'
alias pacdiff 'sudo -H DIFFPROG=meld pacdiff'

# Get the error messages from journalctl
alias jctl 'journalctl -p 3 -xb'

# Recent installed packages
alias rip 'expac --timefmt="%Y-%m-%d %T" "%l\t%n %v" | sort | tail -200 | nl'

## Run fastfetch if session is interactive
if status --is-interactive && type -q fastfetch
   fastfetch --config neofetch.jsonc
end

# Editor
set -x EDITOR nvim
set -x VISUAL nvim

# Proxy settings
set -x http_proxy ''
set -x https_proxy ''
set -x ftp_proxy ''
set -x socks_proxy ''

# PATH additions
set -x PATH $HOME/.cargo/bin $HOME/bin $HOME/.config/composer/vendor/bin $HOME/dotfiles/backup-tools $HOME/dotfiles/bin $PATH

# PHP server helper
functions -e phpserver
function phpserver
    if test -z $argv[1]
        echo "Usage: phpserver <port>"
    else
        php -S localhost:$argv[1] > php.log 2>&1 &
    end
end

# days_old function
function days_old
    echo (math "(date +%s - (stat -c %Y $argv))/86400")
end

alias ls='ls --color=auto -N'
# alias ls='ls --color=auto'
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias la='ls -A'
alias rm='rm -i'
alias ..='cd ..'
alias cd..='cd ..'

alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

alias psg='ps aux | grep'

alias gs='git status'
alias gss='git status -s'
alias gl='git log'
alias glf='git log --name-status --oneline'
alias gb='git log --all --graph --decorate --oneline'
alias ga='git add --verbose'
alias gap='git add -p'
alias gac='git add --verbose .; git commit -v'
alias gpl='git pull'
alias gph='git push'
alias gpr='git pull --rebase'
alias gri='git rebase -i'
alias gc='git commit -v'
alias gca='git commit -av'
alias gsqd='git-summary -qd'
alias gd='git diff'
alias gdc='git diff --cached'
alias gsh='git show'

# Open Git conflicts in $EDITOR
alias fix='$EDITOR -p `git diff --name-only | uniq`'

# Laravel Sail shortcut
alias sail='bash vendor/bin/sail'

alias findd='find . -type d'
alias sync-folders='php ~/dotfiles/backup-tools/sync-folders.php'

# ps aux | grep [ARGS]
alias psaux='ps aux | grep '

# * delete files older that X days
# find .  -mtime +X -exec rm {} \;

alias screenoff='sleep 1; xset dpms force off'

# prevent accidental -r
alias crontab="crontab -i"

alias bytes2kb='numfmt --to iec --format "%8.2f"'

alias vim='nvim'

alias a='php artisan'
alias at='php artisan test'

bind --erase right

# Use custom tab and shift-tab logic
bind \t tab_handler
bind shift-tab shift_tab_handler

bind escape fish_vi_key_bindings

if test -f ~/.phpbrew/bashrc
    source ~/.phpbrew/phpbrew.fish
end

# Default title: includes last command if set
function fish_title
    set userhost (whoami)"@"(hostname -s)
    set dir (prompt_pwd)
    if set -q __last_cmd
        echo "$userhost:$dir - $__last_cmd"
    else
        echo "$userhost:$dir -"
    end
end

# Save the running command
function fish_preexec --on-event fish_preexec
    set -g __last_cmd $argv[1]
end

# Clear the command after it's done
function fish_postexec --on-event fish_postexec
    set -e __last_cmd
end

