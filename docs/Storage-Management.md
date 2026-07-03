# Storage & Volume Engine Management

RoqNAS coordinates storage tasks using native Linux utilities (`zfs`, `zpool`, `mdadm`) executing close to the bare metal.

---

## 1. ZFS Pool Management

ZFS provides transactional, self-healing software RAID configurations.

### Expansion Methods
RoqNAS supports three distinct ZFS growth operations directly from the UI:

#### Method A: Add Another VDev (Striping Expansion)
Extends an existing pool by striping a new virtual device (vdev) array alongside it.
* **Command**: `zpool add -f <pool_name> <layout> <disks...>`
* **Usage**: Select unassigned drives, choose a layout (mirror, raidz1, raidz2), and click "Extend Pool".
* **Warning**: Adding an unmirrored or low-redundancy vdev to a healthy pool exposes the entire pool to a catastrophic loss if that vdev fails.

#### Method B: Replace & Up-Size (Drive Resilvering)
Upgrades a pool's capacity by replacing existing small drives with larger ones, one by one.
* **Command**: `zpool set autoexpand=on <pool_name>` followed by `zpool replace <pool_name> <old_disk> <new_disk>`.
* **Usage**: Select a degraded or small drive in the ZFS list, choose an unassigned larger disk, and initiate "Replace". The system will resilver data. Once all drives are replaced, the pool expands automatically.

#### Method C: RAIDZ VDev Expansion
Attaches a new disk to an existing active RAIDZ vdev (supported natively in ZFS 2.3+).
* **Command**: `zpool attach <pool_name> <vdev_name> <new_disk>`.
* **Usage**: Select an active RAIDZ group, choose a matching capacity disk, and click "Attach to RAIDZ".

---

## 2. MDADM SoftRAID Management

For standard Linux software RAID arrays.

### Actions
* **Create Array**: Creates `md` devices (`/dev/mdX`) using layouts: `raid0`, `raid1`, `raid5`, `raid6`, or `raid10`.
* **Add Spare/Member**: Hot-plugs a new drive to a running array.
  * **Command**: `mdadm --manage /dev/mdX --add <new_disk>`
* **Fail Disk**: Simulates disk failures or detaches failing drives to trigger spare rebuilds.
  * **Command**: `mdadm --manage /dev/mdX --fail <failing_disk>`
* **Remove Disk**: Detaches a failed member safely from an array.
  * **Command**: `mdadm --manage /dev/mdX --remove <disk>`
* **Grow Array capacity**: Expands the number of active member drives.
  * **Command**: `mdadm --grow /dev/mdX --raid-devices=<new_count>` followed by resizing the underlying filesystem (`resize2fs /dev/mdX` or `xfs_growfs /dev/mdX`).
