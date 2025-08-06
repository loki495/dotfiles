#!/usr/bin/env bash

# === Colors ===
RED="\033[0;31m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}=== Docker Compose Generator for PHP Projects ===${RESET}\n"

# === Helpers ===
function prompt_yes_no() {
  local prompt="$1"
  local default_answer="$2" # y/n
  local answer

  while true; do
    read -p "$(echo -e "${CYAN}${prompt} [${default_answer^^}/$( [[ $default_answer == y ]] && echo n || echo y )]:${RESET} ")" answer
    answer="${answer,,}" # lowercase
    if [[ -z "$answer" ]]; then
      answer=$default_answer
    fi
    if [[ "$answer" == "y" || "$answer" == "yes" ]]; then
      return 0
    elif [[ "$answer" == "n" || "$answer" == "no" ]]; then
      return 1
    else
      echo -e "${RED}Please answer y or n.${RESET}"
    fi
  done
}

# === Project Name ===
while true; do
  read -p "$(echo -e "${CYAN}Project name (used as subdomain, e.g. project.dev.local.test):${RESET} ")" PROJECT
  if [[ -z "$PROJECT" ]]; then
    echo -e "${RED}Project name cannot be empty.${RESET}"
  else
    break
  fi
done
PROJECT_SLUG=$(echo "$PROJECT" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# === PHP Version ===
LATEST_PHP="8.4"
PHP_OPTIONS=("5.6" "7.0" "7.1" "7.2" "7.3" "7.4" "8.0" "8.1" "8.2" "8.3" "8.4" "Other")

echo -e "\n${CYAN}${BOLD}Select PHP version:${RESET}"
for i in "${!PHP_OPTIONS[@]}"; do
  printf "  ${YELLOW}%2d)${RESET} %s\n" $((i+1)) "${PHP_OPTIONS[$i]}"
done

while true; do
  read -p "$(echo -e "${CYAN}Choose PHP version [default: ${GREEN}$LATEST_PHP${CYAN}]:${RESET} ")" REPLY
  if [[ -z "$REPLY" ]]; then
    PHP_VERSION="$LATEST_PHP"
    echo -e "✔ Using default PHP version: ${GREEN}${PHP_VERSION}${RESET}"
    break
  elif [[ "$REPLY" =~ ^[0-9]+$ && "$REPLY" -ge 1 && "$REPLY" -le ${#PHP_OPTIONS[@]} ]]; then
    opt="${PHP_OPTIONS[$((REPLY-1))]}"
    if [[ "$opt" == "Other" ]]; then
      while true; do
        read -p "$(echo -e "${CYAN}Enter custom PHP version tag (e.g. 8.0-apache): ${RESET}")" PHP_VERSION
        if [[ -z "$PHP_VERSION" ]]; then
          echo -e "${RED}Version can't be empty.${RESET}"
        else
          break
        fi
      done
    else
      PHP_VERSION="$opt"
    fi
    break
  else
    echo -e "${RED}❌ Invalid choice. Enter a number between 1 and ${#PHP_OPTIONS[@]}, or press Enter for default.${RESET}"
  fi
done

# === Detect Laravel ===
LARAVEL_DETECTED=false
if [[ -f "artisan" && -d "bootstrap" && -d "storage" ]]; then
  LARAVEL_DETECTED=true
  echo -e "\n${GREEN}Laravel project detected.${RESET}"
  if prompt_yes_no "Use 'public' as Apache document root?" "y"; then
    APACHE_ROOT="public"
  else
    while true; do
      read -p "$(echo -e "${CYAN}Enter Apache document root folder relative to project root:${RESET} ")" APACHE_ROOT
      if [[ -z "$APACHE_ROOT" ]]; then
        echo -e "${RED}Document root cannot be empty.${RESET}"
      else
        break
      fi
    done
  fi
else
  echo -e "\n${YELLOW}No Laravel detected.${RESET}"
  while true; do
    read -p "$(echo -e "${CYAN}Enter Apache document root folder relative to project root [default: .]:${RESET} ")" APACHE_ROOT
    APACHE_ROOT=${APACHE_ROOT:-"."}
    # accept '.' or folder name
    break
  done
fi

# === Detect Laravel ===
USE_VITE=false
if [[ -f "vite.config.js" ]]; then
  echo -e "\n${GREEN}Vite detected.${RESET}"
  if prompt_yes_no "Use 'vite' server?" "y"; then
    USE_VITE=true
  fi
fi

# === MariaDB Version ===
echo
read -p "$(echo -e "${CYAN}MariaDB version (put 0 to skip DB) [default: 10.5]:${RESET} ")" MARIADB_VERSION
MARIADB_VERSION=${MARIADB_VERSION:-10.5}
USE_DB=true
if [[ "$MARIADB_VERSION" == "0" ]]; then
  USE_DB=false
fi

# === DB credentials (only if DB enabled) ===
if $USE_DB; then
  echo
  read -p "$(echo -e "${CYAN}MySQL/MariaDB root password [default: root]:${RESET} ")" MYSQL_ROOT_PASSWORD
  MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-root}
  read -p "$(echo -e "${CYAN}MySQL/MariaDB database name [default: app]:${RESET} ")" MYSQL_DATABASE
  MYSQL_DATABASE=${MYSQL_DATABASE:-app}
  read -p "$(echo -e "${CYAN}MySQL/MariaDB user [default: user]:${RESET} ")" MYSQL_USER
  MYSQL_USER=${MYSQL_USER:-user}
  read -p "$(echo -e "${CYAN}MySQL/MariaDB password [default: pass]:${RESET} ")" MYSQL_PASSWORD
  MYSQL_PASSWORD=${MYSQL_PASSWORD:-pass}
fi

# === Create folders ===
mkdir -p public
if $USE_DB; then
  mkdir -p docker/mysql
fi

# === Write docker-compose.yml ===
cat > docker-compose.yml <<EOF
version: "3.8"

volumes:
  mysql-data: {}

services:
  app:
    image: php:${PHP_VERSION}-apache
    container_name: ${PROJECT_SLUG}-app
    restart: unless-stopped
    volumes:
      - ./:/var/www/html
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${PROJECT_SLUG}.rule=Host(\`${PROJECT_SLUG}.dev.local.test\`)"
      - "traefik.http.routers.${PROJECT_SLUG}.entrypoints=web"
      - "traefik.http.services.${PROJECT_SLUG}.loadbalancer.server.port=80"
    command: >
      sh -c "a2enmod rewrite &&
             echo '<Directory /var/www/html>' > /etc/apache2/conf-enabled/allow-override.conf &&
             echo 'AllowOverride All' >> /etc/apache2/conf-enabled/allow-override.conf &&
             echo '</Directory>' >> /etc/apache2/conf-enabled/allow-override.conf &&
             sed -i 's|DocumentRoot .*|DocumentRoot /var/www/html/${APACHE_ROOT}|' /etc/apache2/sites-available/000-default.conf &&
             chown -R www-data:www-data /var/www/html/storage /var/www/html/bootstrap/cache /var/www/html/database 2>/dev/null || true &&
             find /var/www/html/storage -type d -exec chmod 775 {} \; 2>/dev/null || true &&
             find /var/www/html/bootstrap/cache -type d -exec chmod 775 {} \; 2>/dev/null || true &&
             find /var/www/html/database -type d -exec chmod 775 {} \; 2>/dev/null || true &&
             find /var/www/html/storage -type f -exec chmod 644 {} \; 2>/dev/null || true &&
             find /var/www/html/bootstrap/cache -type d -exec chmod 644 {} \; 2>/dev/null || true &&
             find /var/www/html/database -type f -exec chmod 644 {} \; 2>/dev/null || true &&
             apache2-foreground"
    networks:
      - web
EOF

if $USE_VITE; then
cat >> docker-compose.yml <<EOF

  vite:
    image: node:18
    container_name: ${PROJECT_SLUG}-vite
    working_dir: /var/www/html
    command: ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
    volumes:
      - ./:/var/www/html
    ports:
      - "3000:3000"
      - "5173:5173"
    networks:
      - web
EOF
fi

if $USE_DB; then
cat >> docker-compose.yml <<EOF

  db:
    image: mariadb:${MARIADB_VERSION}
    container_name: ${PROJECT_SLUG}-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - ./docker/mysql:/var/lib/mysql
    networks:
      - web
EOF
fi

cat >> docker-compose.yml <<EOF

networks:
  web:
    external: true
EOF

echo -e "\n${GREEN}✅ docker-compose.yml created for project '${PROJECT_SLUG}'.${RESET}"
echo -e "${CYAN}🌐 Accessible at: http://${PROJECT_SLUG}.dev.local.test${RESET}"
echo -e "${CYAN}📂 Apache document root: ./public/${APACHE_ROOT}${RESET}"
if $USE_DB; then
  echo -e "${CYAN}🐬 MariaDB version: ${MARIADB_VERSION}${RESET}"
  echo -e "${CYAN}🔑 DB user: ${MYSQL_USER}  Password: ${MYSQL_PASSWORD}${RESET}"
  echo -e "${YELLOW}ℹ️ To access this DB, use your central Adminer instance with server: '${PROJECT_SLUG}-db'${RESET}"
else
  echo -e "${YELLOW}ℹ️ No database configured.${RESET}"
fi
