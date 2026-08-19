#!/usr/bin/env bash
set -euo pipefail

# === Colors ===
RED="\033[0;31m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
BOLD="\033[1m"
RESET="\033[0m"

DOTFILES_SETUP="${HOME}/dotfiles/misc/docker/setup-dev-container.sh"
if [ ! -f "${DOTFILES_SETUP}" ]; then
  echo -e "${RED}Missing setup script: ${DOTFILES_SETUP}${RESET}"
  exit 1
fi

echo -e "${CYAN}${BOLD}=== Docker Compose Generator for PHP Projects ===${RESET}\n"

# === Helpers ===
function prompt_yes_no() {
  local prompt="$1"
  local default_answer="$2" # y/n
  local answer
  while true; do
    read -p "$(echo -e "${CYAN}${prompt} [${default_answer^^}/$( [[ $default_answer == y ]] && echo n || echo y )]:${RESET} ")" answer
    answer="${answer,,}" # lowercase
    if [[ -z "${answer}" ]]; then
      answer="${default_answer}"
    fi
    if [[ "${answer}" == "y" || "${answer}" == "yes" ]]; then
      return 0
    elif [[ "${answer}" == "n" || "${answer}" == "no" ]]; then
      return 1
    else
      echo -e "${RED}Please answer y or n.${RESET}"
    fi
  done
}

# === Project Name ===
while true; do
  read -p "$(echo -e "${CYAN}Project name (used as subdomain, e.g. project.dev.local.test):${RESET} ")" PROJECT
  if [[ -z "${PROJECT}" ]]; then
    echo -e "${RED}Project name cannot be empty.${RESET}"
  else
    break
  fi
done
PROJECT_SLUG=$(echo "${PROJECT}" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# === PHP Version ===
LATEST_PHP="8.4"
PHP_OPTIONS=("5.6" "7.0" "7.1" "7.2" "7.3" "7.4" "8.0" "8.1" "8.2" "8.3" "8.4" "Other")

echo -e "\n${CYAN}${BOLD}Select PHP version:${RESET}"
for i in "${!PHP_OPTIONS[@]}"; do
  printf "  ${YELLOW}%2d)${RESET} %s\n" $((i+1)) "${PHP_OPTIONS[$i]}"
done

while true; do
  read -p "$(echo -e "${CYAN}Choose PHP version [default: ${GREEN}${LATEST_PHP}${CYAN}]:${RESET} ")" REPLY
  if [[ -z "${REPLY}" ]]; then
    PHP_VERSION="${LATEST_PHP}"
    break
  elif [[ "${REPLY}" =~ ^[0-9]+$ && "${REPLY}" -ge 1 && "${REPLY}" -le ${#PHP_OPTIONS[@]} ]]; then
    opt="${PHP_OPTIONS[$((REPLY-1))]}"
    if [[ "${opt}" == "Other" ]]; then
      while true; do
        read -p "$(echo -e "${CYAN}Enter custom PHP version tag (e.g. 8.0-apache): ${RESET}")" PHP_VERSION
        if [[ -z "${PHP_VERSION}" ]]; then
          echo -e "${RED}Version can't be empty.${RESET}"
        else
          break
        fi
      done
    else
      PHP_VERSION="${opt}"
    fi
    break
  else
    echo -e "${RED}❌ Invalid choice. Enter a number between 1 and ${#PHP_OPTIONS[@]}, or press Enter for default.${RESET}"
  fi
done

echo -e "✔ Using PHP version: ${GREEN}${PHP_VERSION}${RESET}"

# === Detect Laravel & docroot ===
LARAVEL_DETECTED=false
if [[ -f "artisan" && -d "bootstrap" && -d "storage" ]]; then
  LARAVEL_DETECTED=true
  echo -e "\n${GREEN}Laravel project detected.${RESET}"
  if prompt_yes_no "Use 'public' as Apache document root?" "y"; then
    APACHE_ROOT="public"
  else
    while true; do
      read -p "$(echo -e "${CYAN}Enter Apache document root folder relative to project root:${RESET} ")" APACHE_ROOT
      if [[ -z "${APACHE_ROOT}" ]]; then
        echo -e "${RED}Document root cannot be empty.${RESET}"
      else
        break
      fi
    done
  fi
else
  echo -e "\n${YELLOW}No Laravel detected.${RESET}"
  read -p "$(echo -e "${CYAN}Enter Apache document root folder relative to project root [default: .]:${RESET} ")" APACHE_ROOT
  APACHE_ROOT=${APACHE_ROOT:-"."}
fi

# === Vite support ===
USE_VITE=false
if [[ -f "vite.config.js" ]]; then
  echo -e "\n${GREEN}Vite detected.${RESET}"
  if prompt_yes_no "Use 'vite' server?" "y"; then
    USE_VITE=true
  fi
fi

# === Copy setup script ===
mkdir -p docker
mkdir -p docker/logs

cp "${DOTFILES_SETUP}" "./docker/setup-dev-container.sh"

# Compose: write docker-compose.yml with inline dockerfile (dockerfile_inline)
cat > docker-compose.yml <<EOF
name: ${PROJECT_SLUG}

services:
  app:
    container_name: ${PROJECT_SLUG}-app
    restart: unless-stopped
    volumes:
      - ./:/var/www/html
      - ./docker/logs:/var/www/html/logs:rw
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${PROJECT_SLUG}.rule=Host(\`${PROJECT_SLUG}.dev.local.test\`)"
      - "traefik.http.routers.${PROJECT_SLUG}.entrypoints=web"
      - "traefik.http.services.${PROJECT_SLUG}.loadbalancer.server.port=80"
    build:
      context: .
      dockerfile_inline: |
        FROM php:${PHP_VERSION}-apache
        COPY docker/setup-dev-container.sh /tmp/setup.sh
        RUN chmod +x /tmp/setup.sh && /usr/bin/bash /tmp/setup.sh
    networks:
      - web
EOF

if ${USE_VITE}; then
  cat >> docker-compose.yml <<EOF

  vite:
    image: node:18
    container_name: ${PROJECT_SLUG}-vite
    working_dir: /var/www/html
    command: ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
    volumes:
      - ./:/var/www/html
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.${PROJECT_SLUG}-vite.rule=Host(\`vite.${PROJECT_SLUG}.dev.local.test\`)"
      - "traefik.http.routers.${PROJECT_SLUG}-vite.entrypoints=web"
      - "traefik.http.services.${PROJECT_SLUG}-vite.loadbalancer.server.port=5173"
    networks:
      - web
EOF
fi

cat >> docker-compose.yml <<EOF

networks:
  web:
    external: true
EOF

# Ensure .env contains COMPOSE_PROJECT_NAME
ENV_FILE="./.env"
if [ ! -f "${ENV_FILE}" ]; then
  touch "${ENV_FILE}"
fi
grep -v '^COMPOSE_PROJECT_NAME=' "${ENV_FILE}" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "${ENV_FILE}"
echo "COMPOSE_PROJECT_NAME=${PROJECT_SLUG}" >> "${ENV_FILE}"

echo -e "\n${GREEN}✅ docker-compose.yml created (inline Dockerfile) for project '${PROJECT_SLUG}'.${RESET}"
echo -e "${CYAN}🌐 Accessible at: http://${PROJECT_SLUG}.dev.local.test${RESET}"
echo -e "${CYAN}📂 Apache document root: ./${APACHE_ROOT}${RESET}"
echo -e "${YELLOW}ℹ️ Note: This compose does NOT create a per-project DB. Use your central mariadb and point DB host accordingly.${RESET}"
