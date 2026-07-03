# RoqNAS OS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-v0.1.0-blue.svg)](#)
[![OS Support](https://img.shields.io/badge/OS-Debian%2013-red.svg)](#)

A sleek, lightweight, self-hosted Zero-Config Network Attached Storage (NAS) management control plane designed specifically for Debian GNU/Linux systems. 

RoqNAS provides an intuitive web interface to manage physical disks, ZFS pools (including dynamic expansion), MDADM arrays, Samba shares with macOS Apple Time Machine integration, Bonjour mDNS LAN discoverability, and local hypervisor virtual machines.

---

## Key Features

* **📦 Unified Storage Engine**:
  * Create, monitor, and configure **ZFS pools** (ZAP) and datasets.
  * Grow ZFS storage via **Striped VDevs**, **Drive Replacement**, or **RAIDZ Expansion** (ZFS 2.3+).
  * Configure resilient **MDADM software RAID** groups with spare drives, fail actions, and filesystem sizing.
* **🍏 Apple macOS Integration**:
  * Enable **Apple Time Machine** targets over Samba with configurable space caps.
  * Built-in `vfs_fruit` extensions for high-speed file operations and resource fork mapping.
* **⚡ Bonjour LAN Discoverability**:
  * Dynamic multicast DNS (mDNS) broadcasting using Avahi.
  * Zero-config LAN lookup (`roqnas-XXXXXX.local`) for dashboard portals and file shares.
  * Custom representation profiles (Time Capsule, Mac mini, Mac Pro, Xserve) to display native icons in macOS Finder.
* **🛡️ Secure Access & Terminals**:
  * Multi-Factor Authentication (MFA/TOTP) support.
  * Integrated **Web Console Terminal** with secure user re-authentication.
* **⚙️ Network Interfaces & Bonding**:
  * Manage interfaces, MTU limits, and setup Link Aggregation (LAG/Bonds, e.g. 802.3ad LACP).
* **🖥️ KVM Hypervisor Node**:
  * Spin up and manage local kernel-based Virtual Machines (KVM) directly from the dashboard.
* **🚀 Software Update Center**:
  * Embedded Update Manager supporting automated git-based releases (dev, beta, release channels).

---

## ⚡ Single-Line Installation

Set up a fresh Debian 13 system and execute the bootstrapper directly. The installer auto-configures your hostname, deploys system packages, sets up Python virtual environments, builds the Vue 3 dashboard, and registers systemd service daemons automatically.

```bash
curl -sSL https://update.roqnas.org | bash
```

*(For manual installation guidelines, custom update channels, or staging, see the [Installation Guide](docs/Installation-Guide.md))*

---

## Project Structure

```text
roqnas/
├── backend/                  # Python FastAPI control plane application
│   ├── main.py               # API Router, authentication & system commands interface
│   ├── storage.py            # Storage engine interface (ZFS / MDADM / SMART)
│   ├── directory.py          # Active Directory / Samba integrations
│   └── users.json            # Authentication database
├── frontend/                 # Vue 3 SPA Dashboard client
│   ├── src/                  # Components, app layouts, and assets
│   ├── package.json          # Node dependencies definitions
│   └── vite.config.ts        # Vite compiler settings
├── docs/                     # GitHub Wiki documentation bundle
├── deploy.sh                 # Single-line installer bootstrapper
├── install.sh                # Main installer orchestration script
└── LICENSE                   # MIT Open-Source License
```

---

## Documentation Wiki

Refer to the complete documentation bundle located inside the `/docs` directory for wiki pages:
1. [Home / Wiki Welcome](docs/Home.md)
2. [Installation & Staging Guide](docs/Installation-Guide.md)
3. [Storage Engine (ZFS & MDADM)](docs/Storage-Management.md)
4. [Bonjour Discoverability & mDNS](docs/Network-and-Bonjour.md)
5. [Update Server Infrastructure Setup](docs/Update-Server-Setup.md)

---

## License

RoqNAS is open-source software licensed under the [MIT License](LICENSE).
