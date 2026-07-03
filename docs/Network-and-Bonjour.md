# Network & Bonjour Discoverability

RoqNAS integrates networking controls (Link Aggregation, IP configurations) and multicast LAN service discoverability.

---

## 1. Bonjour (mDNS) Discovery

RoqNAS advertises standard services locally via the **Avahi mDNS Stack**.

### Services Advertised
When discoverability is toggled active, the following XML configuration structures are built in `/etc/avahi/services/`:

1. **`smb.service`**: Advertises Samba services (`_smb._tcp`) on port `445` under the host hostname.
2. **`web.service`**: Exposes the administration portal on port `8000` (represented as `<hostname> Management Portal`).
3. **`device-info.service`**: Defines the icon profile visible inside the macOS Finder sidebar:
   ```xml
   <txt-record>model=TimeCapsule</txt-record>
   ```

### Representation Profiles
Admin users can customize the representation model using the **Bonjour Discovery** tab in Network Settings:
* **Time Capsule** (Default): Standard network storage disk icon.
* **Mac mini**: Compact desktop server icon.
* **Mac Pro**: High-power aluminum tower icon.
* **iMac**: Flat-screen workstation icon.
* **Xserve**: Rackmounted enterprise system icon.

---

## 2. Apple Time Machine over Samba (SMB)

To allow Apple macOS clients to back up directly to your RoqNAS storage pool over Samba, the system configures standard compatibility extensions:

### Global Samba Parameters
RoqNAS injects these parameters into `/etc/samba/smb.conf`'s `[global]` block to enable macOS metadata indexing:
```ini
vfs objects = catia fruit streams_xattr
fruit:metadata = netatalk
fruit:veto_appledouble = no
fruit:posix_rename = yes
```

### Share-level parameters
When a Samba share is flagged as an **Apple Time Machine Target**, the backend appends:
```ini
fruit:time machine = yes
fruit:time machine max size = 500G # Optional capacity cap
```

Once published, macOS clients opening *System Settings > General > Time Machine* will automatically discover the share and mount it as a valid backup destination.
