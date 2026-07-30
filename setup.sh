#!/bin/bash

# ==============================================================================
#  Hadoop Handler — Global Setup Installer (Linux & macOS)
#  Developer: Aditya Pidurkar (itsadityap)
# ==============================================================================

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

clear
echo -e "${BLUE}===================================================${NC}"
echo -e "         Hadoop Handler Setup Installer            "
echo -e "        Developer: Aditya Pidurkar (github.com/itsadityapidurkar)    "
echo -e "${BLUE}===================================================${NC}"

# Get directory where setup.sh is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify target tool file exists
TOOL_PATH="${SCRIPT_DIR}/hadoop-handler"
if [ ! -f "$TOOL_PATH" ]; then
    echo -e "${RED}[!] Error: Target script 'hadoop-handler' not found at ${TOOL_PATH}.${NC}"
    exit 1
fi

# Make the tool script executable
echo -e "[+] Setting executable permission on hadoop-handler..."
chmod +x "$TOOL_PATH"

# Setup symlink in /usr/local/bin
echo -e "[+] Installing command to /usr/local/bin/hadoop-handler..."
echo -e "    ${YELLOW}This step requires administrative (sudo) privileges.${NC}"

if sudo ln -sf "$TOOL_PATH" /usr/local/bin/hadoop-handler; then
    echo -e "\n${GREEN}[✓] Hadoop Handler installed successfully!${NC}"
    echo -e "You can now launch the control panel from any directory using: "
    echo -e "    ${YELLOW}hadoop-handler${NC}"
else
    echo -e "\n${RED}[!] Failed to create symlink in /usr/local/bin. Trying local user path...${NC}"
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"
    ln -sf "$TOOL_PATH" "${LOCAL_BIN}/hadoop-handler"
    
    echo -e "${GREEN}[✓] Installed to user local directory.${NC}"
    echo -e "Ensure ${YELLOW}${LOCAL_BIN}${NC} is in your PATH, then run: "
    echo -e "    ${YELLOW}hadoop-handler${NC}"
fi

echo -e "${BLUE}===================================================${NC}"
