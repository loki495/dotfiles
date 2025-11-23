#!/usr/bin/env bash
set -euo pipefail

log()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m%s\033[0m\n' "$*"; }
err()  { printf '\033[0;31m%s\033[0m\n' "$*"; }

# -------------------------------
# Detect package manager / distro
# -------------------------------
PKG_MANAGER=""
if command -v apt-get >/dev/null 2>&1; then
    PKG_MANAGER="apt"
elif command -v apk >/dev/null 2>&1; then
    PKG_MANAGER="apk"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
else
    err "No supported package manager found (apt, apk, dnf, yum). Exiting."
    exit 1
fi
log "Detected package manager: $PKG_MANAGER"

# -------------------------------
# Install system packages
# -------------------------------
if [ "$PKG_MANAGER" = "apt" ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y --no-install-recommends \
        curl wget git vim-tiny jq procps iputils-ping ca-certificates \
        build-essential autoconf pkg-config libtool make unzip \
        libjpeg62-turbo-dev libpng-dev libwebp-dev libfreetype6-dev libxpm-dev \
        libzip-dev zlib1g-dev libonig-dev libxml2-dev \
        openssh-client sudo
    rm -rf /var/lib/apt/lists/*

elif [ "$PKG_MANAGER" = "apk" ]; then
    apk add --no-cache \
        curl wget git vim jq procps iputils ca-certificates \
        build-base autoconf pkgconfig libtool make unzip \
        libjpeg-turbo-dev libpng-dev libwebp-dev freetype-dev libxpm-dev \
        libzip-dev zlib-dev oniguruma-dev libxml2-dev \
        openssh sudo

elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
    PKG_INSTALL="yum -y install"
    command -v dnf >/dev/null 2>&1 && PKG_INSTALL="dnf -y install"
    ${PKG_INSTALL} \
        curl wget git vim-minimal jq procps-ng iputils ca-certificates \
        gcc make autoconf automake libtool pkgconfig unzip \
        libjpeg-turbo-devel libpng-devel libwebp-devel freetype-devel libXpm-devel \
        libzip-devel zlib-devel oniguruma-devel libxml2-devel \
        sudo
fi

# -------------------------------
# Configure Git
# -------------------------------
if command -v git >/dev/null 2>&1; then
    git config --global --add safe.directory /var/www/html || true
    git config --system core.pager cat || true
fi

# -------------------------------
# Fix UID/GID for www-data
# -------------------------------
TARGET_UID=1000
TARGET_GID=1000

if getent group www-data >/dev/null 2>&1; then
    cur_gid=$(getent group www-data | cut -d: -f3)
    if [ "$cur_gid" != "$TARGET_GID" ]; then
        groupmod -g $TARGET_GID www-data || warn "groupmod failed"
    fi
fi

if getent passwd www-data >/dev/null 2>&1; then
    cur_uid=$(getent passwd www-data | cut -d: -f3)
    if [ "$cur_uid" != "$TARGET_UID" ]; then
        usermod -u $TARGET_UID www-data || warn "usermod failed"
    fi
fi

# -------------------------------
# Adjust Apache config for Laravel / custom root
# -------------------------------
if [ -d /etc/apache2 ]; then
    cat <<'EOF' > /etc/apache2/conf-enabled/allow-override.conf
<Directory /var/www/html>
    AllowOverride All
    Require all granted
</Directory>
EOF

fi

# Use the APACHE_ROOT env or ARG passed from Docker
APACHE_ROOT=${APACHE_ROOT:-.}

if [ -f /etc/apache2/sites-available/000-default.conf ]; then
    sed -i "s|DocumentRoot .*|DocumentRoot /var/www/html/${APACHE_ROOT}|" /etc/apache2/sites-available/000-default.conf || true
fi

# -------------------------------
# PHP Extension Installation
# -------------------------------
log "Installing PHP extensions"

# Detect PHP version
PHPVER=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')
log "Detected PHP version: $PHPVER"

# Common extensions
PHP_EXTENSIONS=("bcmath" "ctype" "curl" "dom" "fileinfo" "gd" "mbstring" "mysqli" "pdo_mysql" "zip" "xml" "soap")

# GD configure args
GD_ARGS=""

# PHP < 7.4 uses old style, PHP >= 7.4 uses new style
if [[ "$PHPVER" =~ ^7\.[0-3]$ ]]; then
    GD_ARGS="--with-jpeg-dir=/usr/include --with-freetype-dir=/usr/include --with-webp-dir=/usr/include --with-xpm-dir=/usr/include"
else
    GD_ARGS="--with-jpeg --with-freetype --with-webp --with-xpm"
fi

docker-php-ext-configure gd $GD_ARGS
docker-php-ext-install -j"$(nproc)" gd


for ext in "${PHP_EXTENSIONS[@]}"; do
    if [ "$ext" = "gd" ]; then
        docker-php-ext-configure gd $GD_ARGS
    fi
    docker-php-ext-install -j"$(nproc)" "$ext" || warn "Failed to install PHP extension $ext"
done

# -------------------------------
# Laravel / storage permissions
# -------------------------------
if [ -f "/var/www/html/artisan" ]; then
    log "Adjusting permissions for Laravel"
    mkdir -p /var/www/html/storage /var/www/html/bootstrap/cache
    chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache
    chmod -R 775 /var/www/html/storage /var/www/html/bootstrap/cache
fi

a2enmod rewrite
a2enmod headers
service apache2 restart

# -------------------------------
# Final messages
# -------------------------------
log "✅ Container setup complete"
