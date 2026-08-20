#!/bin/bash

# ==============================================================================
#  Hadoop Handler — Unix Bootstrap Installer (Linux & macOS)
#  Developer: Aditya Pidurkar (itsadityap)
# ==============================================================================

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ -z "$HOME" ]; then
    echo -e "${RED}[!] Error: HOME environment variable is not set.${NC}"
    exit 1
fi

INSTALL_DIR="$HOME/.hadoop-handler"

clear
echo -e "${BLUE}===================================================${NC}"
echo -e "       Bootstrapping Hadoop Handler Installer      "
echo -e "        Developer: Aditya Pidurkar (itsadityap)    "
echo -e "${BLUE}===================================================${NC}"

# Check if git is installed
if ! command -v git >/dev/null 2>&1; then
    echo -e "${RED}[!] Error: 'git' is required to fetch files. Please install git first.${NC}"
    exit 1
fi

echo -e "[+] Cloning repository to ${YELLOW}${INSTALL_DIR}${NC}..."
rm -rf "$INSTALL_DIR"
if git clone https://github.com/itsadityapidurkar/hadoop-handler.git "$INSTALL_DIR"; then
    echo -e "${GREEN}[✓] Repository cloned successfully.${NC}"
    cd "$INSTALL_DIR" || { echo -e "${RED}[!] Error: Failed to access directory.${NC}"; exit 1; }
    chmod +x setup.sh
    ./setup.sh
else
    echo -e "${RED}[!] Error: Failed to clone repository from GitHub.${NC}"
    exit 1
fi
