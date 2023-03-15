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

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

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

alias nvim='~/nvim/AppRun'
alias vim='nvim'
