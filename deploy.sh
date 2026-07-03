#!/usr/bin/env bash
# ==============================================================================
# RoqNAS Single-Line Installer Bootstrapper
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

UPDATE_SERVER="https://update.roqnas.org"
BRANCH="release"

# Parse CLI arguments if any
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --branch) BRANCH="$2"; shift ;;
        --server) UPDATE_SERVER="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo -e "${BLUE}[*] Bootstrapping RoqNAS installation (Branch: ${BRANCH})...${NC}"

# Check for curl or wget
if command -v curl >/dev/null 2>&1; then
    FETCH_CMD="curl -sSL"
elif command -v wget >/dev/null 2>&1; then
    FETCH_CMD="wget -qO-"
else
    echo -e "${RED}[-] Error: Neither curl nor wget is installed. Please install one to continue.${NC}"
    exit 1
fi

# Fetch release manifest
echo -e "${BLUE}[*] Querying latest version info from ${UPDATE_SERVER}...${NC}"
MANIFEST_URL="${UPDATE_SERVER}/api/version?branch=${BRANCH}"

MANIFEST=$($FETCH_CMD "${MANIFEST_URL}" || true)

if [ -z "$MANIFEST" ]; then
    echo -e "${YELLOW}[!] Warning: Update server is unreachable or returned empty manifest. Falling back to default download URL.${NC}"
    DOWNLOAD_URL="https://github.com/roqnas/roqnas/archive/refs/tags/latest.tar.gz"
else
    DOWNLOAD_URL=$(echo "${MANIFEST}" | grep -o -E '"download_url"\s*:\s*"[^"]+"' | cut -d'"' -f4 || true)
fi

if [ -z "$DOWNLOAD_URL" ]; then
    echo -e "${RED}[-] Error: Could not resolve download URL from manifest.${NC}"
    exit 1
fi

TEMP_TAR="/tmp/roqnas_latest.tar.gz"
TEMP_DIR="/tmp/roqnas_install_staging"

# Cleanup trap
cleanup() {
    rm -f "${TEMP_TAR}" || true
    rm -rf "${TEMP_DIR}" || true
}
trap cleanup EXIT

echo -e "${BLUE}[*] Downloading release from ${DOWNLOAD_URL}...${NC}"
if command -v curl >/dev/null 2>&1; then
    curl -L -o "${TEMP_TAR}" "${DOWNLOAD_URL}"
else
    wget -O "${TEMP_TAR}" "${DOWNLOAD_URL}"
fi

echo -e "${BLUE}[*] Extracting package...${NC}"
mkdir -p "${TEMP_DIR}"
tar -xzf "${TEMP_TAR}" -C "${TEMP_DIR}"

# Locate install.sh and run it
INSTALL_SCRIPT=""
while IFS= read -r -d '' file; do
    if [[ "$(basename "$file")" == "install.sh" ]]; then
        INSTALL_SCRIPT="$file"
        break
    fi
done < <(find "${TEMP_DIR}" -name "install.sh" -print0)

if [ -z "$INSTALL_SCRIPT" ]; then
    echo -e "${RED}[-] Error: install.sh not found inside release package.${NC}"
    exit 1
fi

cd "$(dirname "${INSTALL_SCRIPT}")"
chmod +x install.sh
./install.sh
