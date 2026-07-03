# RoqNAS Installation Guide

This page details how to deploy RoqNAS OS on bare metal, virtual machines, or local development sandboxes.

---

## System Requirements

| Specification | Minimum Requirement | Recommended |
|:---|:---|:---|
| **Operating System** | Debian 13 (Trixie) Minimal | Debian 13 Minimal |
| **CPU Architecture** | x86_64 or ARM (v7/v8) | Multicore x86_64 or ARM64 |
| **Memory (RAM)** | 1 GB (without ZFS) | 4 GB+ (if using ZFS) |
| **OS Drive** | 8 GB capacity | SSD (SATA or NVMe) |
| **Network** | 1 Gbps Ethernet NIC | 10 Gbps Ethernet NIC (or Bonds) |
| **Data Drives** | 1+ Unassigned Storage Drives | Multiple identical drives for RAID |

---

## Installation Methods

### Method 1: The Single-Line Bootstrapper (Recommended)
Log in to your fresh Debian system as `root` (or a user with `sudo` privileges) and execute:

```bash
curl -sSL https://update.roqnas.org | bash
```

The bootstrapper automatically:
1. Queries the Update Center for the latest stable release tarball.
2. Resolves primary NIC MAC address to generate unique hostname (`roqnas-XXXXXX`).
3. Installs dependencies (`samba`, `mdadm`, `zfsutils-linux`, `avahi-daemon`, `libvirt`, `nodejs`).
4. Compiles Vue 3 SPA frontend assets.
5. Deploys background control services and registers them in `systemd`.

---

## Manual / Staging Installation

If you are a developer deploying from a cloned repository:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/roqnas/roqnas.git /opt/roqnas
   cd /opt/roqnas
   ```

2. **Trigger the Installer Script**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Verify Daemon Active status**:
   ```bash
   systemctl status roqnas-backend.service
   ```

4. **Access the portal**:
   Open your browser and navigate to: `http://<YOUR_SERVER_IP>:8000/`

---

## Default Credentials

* **System Admin Portal**:
  * **Username**: `admin`
  * **Password**: `admin`
  * *Note: If MFA was configured in a previous build, you will be prompted for your TOTP code during login.*
