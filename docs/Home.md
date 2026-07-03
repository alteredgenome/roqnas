# Welcome to the RoqNAS OS Wiki

Welcome to the official developer and administrator documentation wiki for **RoqNAS OS**. 

RoqNAS is a lightweight, zero-configuration NAS management platform built for Debian GNU/Linux systems. It abstracts complex storage and networking configurations behind an intuitive, modern, responsive glassmorphism web control panel.

---

## Wiki Navigation Directory

Use the sidebar or links below to explore specific documentation sections:

### 🚀 Getting Started
* **[Installation Guide](Installation-Guide.md)**: Standard system requirements, single-line script installers, offline builds, and setup.

### 💾 Storage & File Systems
* **[Storage Engine Manual](Storage-Management.md)**: Configuring and expanding ZFS pools (Add VDevs, Resilver replacements, RAIDZ grow actions) and managing MDADM arrays.

### 🌐 LAN Discoverability & Sharing
* **[Network & Bonjour Discovery](Network-and-Bonjour.md)**: Setting up Samba (SMB) file shares with macOS Apple Time Machine integration and configuring Avahi multicast DNS (mDNS) client icons.

### ⚙️ Infrastructure & Updates
* **[Update Server Setup](Update-Server-Setup.md)**: How to host your own private update server behind a secure BunkerWeb Web Application Firewall (WAF) reverse proxy.

---

## Architecture Overview

RoqNAS is built upon a decoupling model:

1. **Host OS (Debian 13)**: Native services run close to bare metal to ensure maximum file IO throughput.
2. **FastAPI Engine (Backend)**: Python-based control plane executing command interfaces, security checks, state validation, and exposing REST APIs. Runs under a secure systemd service.
3. **Vue 3 SPA Dashboard (Frontend)**: Standard client-side UI compiling into static web pages served directly from the control plane's webserver.
