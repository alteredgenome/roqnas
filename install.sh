#!/usr/bin/env bash
# ==============================================================================
# RockNAS OS Installer Bootstrapper
# Idempotent system deployer for pristine Debian 13 (Trixie) architectures.
# ==============================================================================

set -eo pipefail

# Style definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}             RockNAS OS Control Plane Bootstrapper Installer          ${NC}"
echo -e "${CYAN}======================================================================${NC}"

# 1. Root privilege verification
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Warning: Not executing as root. Sudo privilege elevation may be requested.${NC}"
    SUDO="sudo"
else
    SUDO=""
fi

# Resolve script directory (absolute path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
FRONTEND_DIR="${SCRIPT_DIR}/frontend"

# Rename system hostname based on MAC address
echo -e "${BLUE}[*] Resolving primary interface MAC address for hostname generation...${NC}"
PRIMARY_IFACE=$(ip route | grep '^default' | grep -o -E 'dev [a-z0-9]+' | cut -d' ' -f2 || true)
if [ -z "$PRIMARY_IFACE" ]; then
    PRIMARY_IFACE=$(ip -o link show | awk -F': ' '$3 !~ /lo/ {print $2}' | head -n1 | tr -d ' ' || true)
fi

NEW_HOSTNAME="roqnas-xxxxxx"
if [ -n "$PRIMARY_IFACE" ] && [ -f "/sys/class/net/${PRIMARY_IFACE}/address" ]; then
    MAC_ADDR=$(cat "/sys/class/net/${PRIMARY_IFACE}/address")
    SUFFIX=$(echo "${MAC_ADDR}" | tr -d ':' | grep -o -E '.{6}$' || true)
    if [ -n "$SUFFIX" ]; then
        NEW_HOSTNAME="roqnas-${SUFFIX}"
    fi
fi

echo -e "${GREEN}[*] Setting system hostname to ${NEW_HOSTNAME}...${NC}"
$SUDO hostnamectl set-hostname "${NEW_HOSTNAME}" || true
$SUDO sed -i "s/127.0.1.1.*/127.0.1.1\t${NEW_HOSTNAME}/" /etc/hosts || true

# Check OS version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "${BLUE}[*] Target System identified: ${NAME} ${VERSION_ID} (${CODENAME})${NC}"
fi

# 2. Package installs
enable_debian_extra_repos() {
    echo -e "${BLUE}[*] Checking Debian contrib and non-free components...${NC}"
    # Check DEB822 style sources format (Debian 12+)
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then
        if $SUDO grep -q "Components:" /etc/apt/sources.list.d/debian.sources; then
            if ! $SUDO grep -q "contrib" /etc/apt/sources.list.d/debian.sources; then
                echo -e "${BLUE}[*] Adding contrib, non-free, and non-free-firmware to debian.sources components...${NC}"
                $SUDO sed -i 's/Components: main$/Components: main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources
                $SUDO sed -i 's/Components: main /Components: main contrib non-free non-free-firmware /g' /etc/apt/sources.list.d/debian.sources
            fi
        fi
    fi
    # Check traditional sources.list format
    if [ -f /etc/apt/sources.list ]; then
        if ! $SUDO grep -q "contrib" /etc/apt/sources.list; then
            echo -e "${BLUE}[*] Adding contrib, non-free, and non-free-firmware to sources.list...${NC}"
            $SUDO sed -i 's/main$/main contrib non-free non-free-firmware/g' /etc/apt/sources.list
            $SUDO sed -i 's/main /main contrib non-free non-free-firmware /g' /etc/apt/sources.list
        fi
    fi
}

enable_debian_extra_repos

echo -e "${BLUE}[*] Triggering APT repositories update...${NC}"
$SUDO apt-get update -y || echo -e "${YELLOW}[!] APT Update failed. Proceeding anyway...${NC}"

CORE_DEPS=(
    python3-pip
    python3-venv
    samba
    nfs-kernel-server
    tgt
    nodejs
    npm
    avahi-daemon
    libnss-mdns
)

echo -e "${BLUE}[*] Installing core system dependencies via APT...${NC}"
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y "${CORE_DEPS[@]}" || {
    echo -e "${RED}[-] Error: Failed to install core system dependencies.${NC}"
    exit 1
}

OPTIONAL_DEPS=(
    mdadm
    zfsutils-linux
    libvirt-daemon-system
    python3-libvirt
)

for pkg in "${OPTIONAL_DEPS[@]}"; do
    echo -e "${BLUE}[*] Installing package: $pkg...${NC}"
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y "$pkg" || {
        echo -e "${YELLOW}[!] Warning: Optional package '$pkg' failed to install. Continuing...${NC}"
    }
done

# 3. Setup Python virtual environment
echo -e "${BLUE}[*] Building Python virtual environment...${NC}"
cd "${BACKEND_DIR}"
python3 -m venv --system-site-packages venv
echo -e "${BLUE}[*] Installing backend dependencies...${NC}"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install fastapi uvicorn psutil websockets pyjwt cryptography

# 4. Build Frontend Assets
echo -e "${BLUE}[*] Installing Node dependencies and building Vue 3 SPA...${NC}"
cd "${FRONTEND_DIR}"
# Use --legacy-peer-deps to prevent potential dependency conflicts
npm install --legacy-peer-deps
npm run build

# 5. Set up Systemd Daemon Service
echo -e "${BLUE}[*] Deploying systemd services...${NC}"

# Disable legacy service if active
if $SUDO systemctl is-active rocknas-backend.service >/dev/null 2>&1; then
    echo -e "${YELLOW}[*] Stopping legacy rocknas-backend service...${NC}"
    $SUDO systemctl stop rocknas-backend.service || true
    $SUDO systemctl disable rocknas-backend.service || true
    $SUDO rm -f /etc/systemd/system/rocknas-backend.service || true
fi

SERVICE_CONTENT="[Unit]
Description=RoqNAS Control Plane Engine Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${BACKEND_DIR}
ExecStart=${BACKEND_DIR}/venv/bin/python3 ${BACKEND_DIR}/main.py
Restart=always
RestartSec=5
Environment=ROQNAS_MOCK=false
Environment=ROQNAS_JWT_SECRET=roqnas_super_secret_key_1337

[Install]
WantedBy=multi-user.target"

# Write service file
echo "${SERVICE_CONTENT}" | $SUDO tee /etc/systemd/system/roqnas-backend.service > /dev/null

# Reload systemd and start service
echo -e "${BLUE}[*] Loading service unit and launching backend...${NC}"
$SUDO systemctl daemon-reload
$SUDO systemctl enable roqnas-backend.service
$SUDO systemctl restart roqnas-backend.service

echo -e "${GREEN}======================================================================${NC}"
echo -e "${GREEN}              RoqNAS Installation completed successfully!            ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "${CYAN}Access Control Center Panel URL: http://localhost:8000/${NC}"
echo -e "${CYAN}To view backend logs: journalctl -u roqnas-backend.service -f${NC}"
echo -e "${GREEN}======================================================================${NC}"
