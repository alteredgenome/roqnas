import json
import logging
import os
import subprocess
import re

logger = logging.getLogger("roqnas.storage")

class StorageManager:
    def __init__(self, mock: bool = False):
        self.mock = mock
        if self.mock:
            logger.info("Initializing StorageManager in Mock Mode")
            self._mock_disks = [
                {"name": "sda", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
                {"name": "sdb", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
                {"name": "sdc", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
                {"name": "sdd", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
                {"name": "sde", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
                {"name": "sdf", "size": "1.8T", "type": "disk", "vendor": "ATA", "model": "Samsung_SSD_870", "mountpoint": None, "fstype": None, "children": []},
            ]
            self._mock_mdadm_arrays = {}
            self._mock_zpools = {}
            self._mock_zfs_datasets = {}
            self._mock_zfs_snapshots = {}
            self._mock_zvols = {}

    def _execute(self, cmd: list, check: bool = True) -> str:
        """Helper to run shell commands safely."""
        logger.info(f"Executing: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=check)
            return res.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)} - Error: {e.stderr}")
            raise Exception(e.stderr.strip() or str(e))

    def get_block_devices(self) -> list:
        """Query block devices via lsblk and ZFS Zvols."""
        devices = []
        if self.mock:
            devices = list(self._mock_disks)
            # Add mdadm arrays as block devices
            for name, arr in self._mock_mdadm_arrays.items():
                devices.append({
                    "name": name,
                    "size": "5.4T",
                    "type": "raid",
                    "vendor": "MOCK",
                    "model": f"RAID-{arr['level']} Volume",
                    "mountpoint": arr.get("mountpoint"),
                    "fstype": arr.get("fstype")
                })
            # Add Zvols as block devices
            for fullname, zvol in self._mock_zvols.items():
                devices.append({
                    "name": f"zvol/{fullname}",
                    "size": f"{zvol['size_gb']}G",
                    "type": "zvol",
                    "vendor": "ZFS",
                    "model": f"Zvol Volume {zvol['name']}",
                    "mountpoint": zvol.get("mountpoint"),
                    "fstype": zvol.get("fstype")
                })
            return devices

        try:
            out = self._execute(["lsblk", "-J", "-o", "NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT,MODEL,VENDOR,TYPE"])
            data = json.loads(out)
            devices = data.get("blockdevices", [])
        except Exception as e:
            logger.error(f"Failed to query block devices: {e}")
            sys_block = "/sys/class/block"
            if os.path.exists(sys_block):
                for name in os.listdir(sys_block):
                    if name.startswith(("sd", "vd", "nvme", "md", "zd")):
                        devices.append({
                            "name": name,
                            "size": "Unknown",
                            "type": "raid" if name.startswith("md") else ("zvol" if name.startswith("zd") else "disk"),
                            "vendor": "Generic",
                            "model": name,
                            "mountpoint": None,
                            "fstype": None
                        })

        zvol_root = "/dev/zvol"
        if os.path.exists(zvol_root):
            for dirpath, _, filenames in os.walk(zvol_root):
                for filename in filenames:
                    fullname = os.path.join(dirpath, filename)
                    name = fullname.replace(zvol_root + "/", "")
                    resolved = os.path.realpath(fullname)
                    resolved_name = os.path.basename(resolved)
                    if not any(d.get("name") == resolved_name or d.get("name") == name for d in devices):
                        size = "Unknown"
                        try:
                            sz_out = self._execute(["blockdev", "--getsize64", fullname], check=False)
                            sz_bytes = int(sz_out.strip())
                            size = f"{sz_bytes // (1024**3)}G"
                        except Exception:
                            pass
                        devices.append({
                            "name": f"zvol/{name}",
                            "size": size,
                            "type": "zvol",
                            "vendor": "ZFS",
                            "model": f"Zvol {filename}",
                            "mountpoint": None,
                            "fstype": None
                        })

        return devices

    def create_mdadm_array(self, name: str, level: int, disks: list, fstype: str = "ext4") -> dict:
        """Create an mdadm RAID array and format it."""
        # Sanitize inputs
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("RAID array name must match /dev/mdX layout (e.g. md0, md127)")
        if level not in [0, 1, 5, 6, 10]:
            raise ValueError("RAID level must be 0, 1, 5, 6, or 10")
        for disk in disks:
            if not re.match(r"^[a-zA-Z0-9/_\-]+$", disk):
                raise ValueError(f"Invalid disk path: {disk}")
        if fstype not in ["ext4", "xfs", "none"]:
            raise ValueError("Supported filesystems are ext4, xfs, and none")

        dev_path = f"/dev/{name}"

        if self.mock:
            # Mark disks as assigned by setting fstype / mountpoint
            for d in self._mock_disks:
                if f"/dev/{d['name']}" in disks or d["name"] in disks:
                    d["fstype"] = "linux_raid_member"
                    d["mountpoint"] = dev_path

            self._mock_mdadm_arrays[name] = {
                "name": name,
                "level": level,
                "disks": disks,
                "fstype": fstype if fstype != "none" else None,
                "mountpoint": f"/mnt/{name}" if fstype != "none" else None,
                "status": "clean"
            }
            return self._mock_mdadm_arrays[name]

        # 1. Zero superblock of devices to clean them
        for disk in disks:
            path = disk if disk.startswith("/dev/") else f"/dev/{disk}"
            try:
                self._execute(["mdadm", "--zero-superblock", "--force", path], check=False)
            except Exception:
                pass

        # 2. Create the array
        cmd = [
            "mdadm", "--create", dev_path,
            f"--level={level}",
            f"--raid-devices={len(disks)}",
            *disks,
            "--run"
        ]
        self._execute(cmd)

        # 3. Create Filesystem
        if fstype == "ext4":
            self._execute(["mkfs.ext4", "-F", dev_path])
        elif fstype == "xfs":
            self._execute(["mkfs.xfs", "-f", dev_path])

        # 4. Mount directory
        mount_dir = None
        if fstype != "none":
            mount_dir = f"/mnt/{name}"
            os.makedirs(mount_dir, exist_ok=True)
            self._execute(["mount", dev_path, mount_dir])

        return {
            "name": name,
            "level": level,
            "disks": disks,
            "fstype": fstype if fstype != "none" else None,
            "mountpoint": mount_dir,
            "status": "clean"
        }

    def get_mdadm_arrays(self) -> list:
        """List active mdadm arrays."""
        if self.mock:
            return list(self._mock_mdadm_arrays.values())

        arrays = []
        if not os.path.exists("/proc/mdstat"):
            return arrays

        # Parse /proc/mdstat
        with open("/proc/mdstat", "r") as f:
            content = f.read()

        # Find md devices
        md_devs = re.findall(r"(md\d+) : active raid(\d+)", content)
        for name, level in md_devs:
            # query detailed info via mdadm
            dev_path = f"/dev/{name}"
            status = "unknown"
            disks = []
            try:
                details = self._execute(["mdadm", "--detail", dev_path], check=False)
                # extract state and devices
                state_match = re.search(r"State : (.+)", details)
                if state_match:
                    status = state_match.group(1).strip()
                
                # find active devices
                dev_lines = re.findall(r"/dev/sd[a-z]\d*|/dev/vd[a-z]\d*", details)
                disks = list(set(dev_lines))
            except Exception:
                pass

            # check mount
            mountpoint = None
            try:
                mounts = self._execute(["mount"])
                m_match = re.search(fr"{dev_path} on (.+?) type", mounts)
                if m_match:
                    mountpoint = m_match.group(1).strip()
            except Exception:
                pass

            arrays.append({
                "name": name,
                "level": int(level),
                "disks": disks,
                "mountpoint": mountpoint,
                "status": status
            })

        return arrays

    def add_mdadm_disk(self, name: str, disk: str) -> bool:
        """Add a disk/spare to an existing mdadm array."""
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("Invalid mdadm array name")
        if not re.match(r"^[a-zA-Z0-9/_\-]+$", disk):
            raise ValueError("Invalid disk path")

        disk_path = disk if disk.startswith("/dev/") else f"/dev/{disk}"

        if self.mock:
            if name in self._mock_mdadm_arrays:
                if disk_path not in self._mock_mdadm_arrays[name]["disks"]:
                    self._mock_mdadm_arrays[name]["disks"].append(disk_path)
                for d in self._mock_disks:
                    if d["name"] in disk:
                        d["fstype"] = "linux_raid_member"
                        d["mountpoint"] = f"/dev/{name}"
                return True
            return False

        self._execute(["mdadm", "--manage", f"/dev/{name}", "--add", disk_path])
        return True

    def grow_mdadm_array(self, name: str, new_num_devices: int) -> bool:
        """Grow mdadm array to include newly added spare disks and resize filesystem."""
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("Invalid mdadm array name")

        dev_path = f"/dev/{name}"

        if self.mock:
            if name in self._mock_mdadm_arrays:
                self._mock_mdadm_arrays[name]["status"] = "growing"
                return True
            return False

        # Grow array
        self._execute(["mdadm", "--grow", dev_path, f"--raid-devices={new_num_devices}"])

        # Attempt to resize the underlying filesystem if it's mounted
        # Check if mounted and what filesystem it is
        try:
            mounts = self._execute(["mount"])
            m_match = re.search(fr"{dev_path} on (.+?) type (.+?) ", mounts)
            if m_match:
                mountpoint = m_match.group(1).strip()
                fstype = m_match.group(2).strip()
                if fstype == "ext4" or fstype == "ext3":
                    self._execute(["resize2fs", dev_path])
                elif fstype == "xfs":
                    self._execute(["xfs_growfs", mountpoint])
        except Exception as e:
            logger.error(f"Failed to auto-grow filesystem on {dev_path}: {e}")

        return True

    def fail_mdadm_disk(self, name: str, disk: str) -> bool:
        """Mark a disk in an mdadm array as failed."""
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("Invalid mdadm array name")
        if not re.match(r"^[a-zA-Z0-9/_\-]+$", disk):
            raise ValueError("Invalid disk path")

        disk_path = disk if disk.startswith("/dev/") else f"/dev/{disk}"

        if self.mock:
            if name in self._mock_mdadm_arrays:
                self._mock_mdadm_arrays[name]["status"] = "degraded"
                return True
            return False

        self._execute(["mdadm", "--manage", f"/dev/{name}", "--fail", disk_path])
        return True

    def remove_mdadm_disk(self, name: str, disk: str) -> bool:
        """Remove a failed/spare disk from an mdadm array."""
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("Invalid mdadm array name")
        if not re.match(r"^[a-zA-Z0-9/_\-]+$", disk):
            raise ValueError("Invalid disk path")

        disk_path = disk if disk.startswith("/dev/") else f"/dev/{disk}"

        if self.mock:
            if name in self._mock_mdadm_arrays:
                disks = self._mock_mdadm_arrays[name]["disks"]
                disks = [x for x in disks if x != disk_path and x != disk]
                self._mock_mdadm_arrays[name]["disks"] = disks
                for d in self._mock_disks:
                    if d["name"] in disk:
                        d["fstype"] = None
                        d["mountpoint"] = None
                return True
            return False

        self._execute(["mdadm", "--manage", f"/dev/{name}", "--remove", disk_path])
        
        # Zero superblock of removed device so it shows as clean/available
        try:
            self._execute(["mdadm", "--zero-superblock", "--force", disk_path], check=False)
        except Exception:
            pass

        return True

    def remove_mdadm_array(self, name: str) -> bool:
        """Stop and delete mdadm array."""
        if not re.match(r"^md[0-9]+$", name):
            raise ValueError("Invalid mdadm array name")

        if self.mock:
            if name in self._mock_mdadm_arrays:
                array = self._mock_mdadm_arrays.pop(name)
                for d in self._mock_disks:
                    if d["mountpoint"] == f"/dev/{name}":
                        d["fstype"] = None
                        d["mountpoint"] = None
                return True
            return False

        dev_path = f"/dev/{name}"
        # Unmount
        try:
            self._execute(["umount", "-f", dev_path], check=False)
        except Exception:
            pass

        # Find member disks before stopping the array
        disks = []
        try:
            details = self._execute(["mdadm", "--detail", dev_path], check=False)
            disks = re.findall(r"/dev/sd[a-z]\d*|/dev/vd[a-z]\d*", details)
        except Exception:
            pass

        # Stop array
        self._execute(["mdadm", "--stop", dev_path])

        # Zero superblocks of member disks after stopping
        for disk in disks:
            try:
                self._execute(["mdadm", "--zero-superblock", "--force", disk], check=False)
            except Exception:
                pass

        return True

    def create_zpool(self, name: str, layout: str, disks: list) -> dict:
        """Create a ZFS pool."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid zpool name")
        if layout not in ["striped", "mirror", "raidz1", "raidz2"]:
            raise ValueError("Invalid ZFS layout")
        for disk in disks:
            if not re.match(r"^[a-zA-Z0-9/]+$", disk):
                raise ValueError(f"Invalid disk name: {disk}")

        if self.mock:
            for d in self._mock_disks:
                if f"/dev/{d['name']}" in disks or d["name"] in disks:
                    d["fstype"] = "zfs_member"
                    d["mountpoint"] = f"zpool:{name}"

            self._mock_zpools[name] = {
                "name": name,
                "layout": layout,
                "disks": disks,
                "status": "ONLINE",
                "mountpoint": f"/{name}"
            }
            self._mock_zfs_datasets[name] = {
                "name": name,
                "pool": name,
                "mountpoint": f"/{name}",
                "used": "128K",
                "available": "5.4T"
            }
            return self._mock_zpools[name]

        # Build command: zpool create -f <name> <layout> <disks>
        cmd = ["zpool", "create", "-f", name]
        if layout == "mirror":
            cmd.append("mirror")
        elif layout == "raidz1":
            cmd.append("raidz1")
        elif layout == "raidz2":
            cmd.append("raidz2")
        # Striped doesn't need layout parameter in command line

        cmd.extend(disks)
        self._execute(cmd)

        return {
            "name": name,
            "layout": layout,
            "disks": disks,
            "status": "ONLINE",
            "mountpoint": f"/{name}"
        }

    def get_zpools(self) -> list:
        """List current zpools."""
        if self.mock:
            return list(self._mock_zpools.values())

        pools = []
        try:
            out = self._execute(["zpool", "list", "-H", "-o", "name,health,altroot"])
            for line in out.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    pname = parts[0]
                    health = parts[1]
                    # query status to get devices
                    disks = []
                    try:
                        status_out = self._execute(["zpool", "status", pname])
                        # parse disk names from status
                        disks = list(set(re.findall(r"sd[a-z]\d*|vd[a-z]\d*", status_out)))
                    except Exception:
                        pass

                    pools.append({
                        "name": pname,
                        "layout": "unknown", # would need deeper parsing
                        "disks": disks,
                        "status": health,
                        "mountpoint": f"/{pname}"
                    })
        except Exception as e:
            logger.error(f"Failed to query zpools: {e}")

        return pools

    def add_zpool_vdev(self, name: str, layout: str, disks: list) -> bool:
        """Add a new vdev to an existing ZFS pool."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid zpool name")
        if layout not in ["striped", "mirror", "raidz1", "raidz2"]:
            raise ValueError("Invalid ZFS layout")
        for disk in disks:
            if not re.match(r"^[a-zA-Z0-9/]+$", disk):
                raise ValueError(f"Invalid disk name: {disk}")

        if self.mock:
            if name in self._mock_zpools:
                self._mock_zpools[name]["disks"].extend(disks)
                for d in self._mock_disks:
                    if f"/dev/{d['name']}" in disks or d["name"] in disks:
                        d["fstype"] = "zfs_member"
                        d["mountpoint"] = f"zpool:{name}"
                return True
            return False

        cmd = ["zpool", "add", "-f", name]
        if layout == "mirror":
            cmd.append("mirror")
        elif layout == "raidz1":
            cmd.append("raidz1")
        elif layout == "raidz2":
            cmd.append("raidz2")
        cmd.extend(disks)
        self._execute(cmd)
        return True

    def replace_zpool_disk(self, pool_name: str, old_disk: str, new_disk: str) -> bool:
        """Replace a disk in a ZFS pool and trigger resilvering."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", pool_name):
            raise ValueError("Invalid zpool name")
        if not re.match(r"^[a-zA-Z0-9/]+$", old_disk) or not re.match(r"^[a-zA-Z0-9/]+$", new_disk):
            raise ValueError("Invalid disk names")

        if self.mock:
            if pool_name in self._mock_zpools:
                pool_disks = self._mock_zpools[pool_name]["disks"]
                pool_disks = [new_disk if (x == old_disk or x == f"/dev/{old_disk}") else x for x in pool_disks]
                self._mock_zpools[pool_name]["disks"] = pool_disks
                for d in self._mock_disks:
                    if d["name"] in old_disk:
                        d["fstype"] = None
                        d["mountpoint"] = None
                    if d["name"] in new_disk:
                        d["fstype"] = "zfs_member"
                        d["mountpoint"] = f"zpool:{pool_name}"
                return True
            return False

        # Ensure autoexpand is enabled so the pool grows when larger disks are fully resilvered
        self._execute(["zpool", "set", "autoexpand=on", pool_name])
        # Execute the replacement
        self._execute(["zpool", "replace", pool_name, old_disk, new_disk])
        return True

    def expand_raidz(self, pool_name: str, vdev: str, new_disk: str) -> bool:
        """Attach a disk to expand a RAIDZ vdev (RAIDZ Expansion)."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", pool_name):
            raise ValueError("Invalid zpool name")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", vdev):
            raise ValueError("Invalid vdev name")
        if not re.match(r"^[a-zA-Z0-9/]+$", new_disk):
            raise ValueError("Invalid disk name")

        if self.mock:
            if pool_name in self._mock_zpools:
                self._mock_zpools[pool_name]["disks"].append(new_disk)
                for d in self._mock_disks:
                    if d["name"] in new_disk:
                        d["fstype"] = "zfs_member"
                        d["mountpoint"] = f"zpool:{pool_name}"
                return True
            return False

        # ZFS attach cmd to add a drive to a raidz vdev
        self._execute(["zpool", "attach", pool_name, vdev, new_disk])
        return True

    def destroy_zpool(self, name: str) -> bool:
        """Destroy a ZFS pool."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid zpool name")

        if self.mock:
            if name in self._mock_zpools:
                self._mock_zpools.pop(name)
                # remove associated datasets & snapshots
                self._mock_zfs_datasets = {k: v for k, v in self._mock_zfs_datasets.items() if not k.startswith(name)}
                self._mock_zfs_snapshots = {k: v for k, v in self._mock_zfs_snapshots.items() if not k.startswith(name)}
                # free disks
                for d in self._mock_disks:
                    if d["mountpoint"] == f"zpool:{name}":
                        d["fstype"] = None
                        d["mountpoint"] = None
                return True
            return False

        self._execute(["zpool", "destroy", name])
        return True

    def create_zfs_dataset(self, pool_name: str, dataset_name: str, options: dict = None) -> dict:
        """Create a ZFS dataset in a pool."""
        full_name = f"{pool_name}/{dataset_name}"
        if not re.match(r"^[a-zA-Z0-9_\-\/]+$", full_name):
            raise ValueError("Invalid ZFS dataset path")

        if self.mock:
            self._mock_zfs_datasets[full_name] = {
                "name": full_name,
                "pool": pool_name,
                "mountpoint": f"/{full_name}",
                "used": "64K",
                "available": "5.4T"
            }
            return self._mock_zfs_datasets[full_name]

        cmd = ["zfs", "create"]
        if options:
            for k, v in options.items():
                cmd.extend(["-o", f"{k}={v}"])
        cmd.append(full_name)
        
        self._execute(cmd)
        return {
            "name": full_name,
            "pool": pool_name,
            "mountpoint": f"/{full_name}",
            "used": "0",
            "available": "Unknown"
        }

    def get_zfs_datasets(self) -> list:
        """List all ZFS datasets."""
        if self.mock:
            return list(self._mock_zfs_datasets.values())

        datasets = []
        try:
            out = self._execute(["zfs", "list", "-H", "-o", "name,mountpoint,used,avail"])
            for line in out.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    name = parts[0]
                    pool = name.split("/")[0]
                    datasets.append({
                        "name": name,
                        "pool": pool,
                        "mountpoint": parts[1],
                        "used": parts[2],
                        "available": parts[3]
                    })
        except Exception as e:
            logger.error(f"Failed to query ZFS datasets: {e}")

        return datasets

    def destroy_zfs_dataset(self, name: str) -> bool:
        """Destroy a dataset."""
        if not re.match(r"^[a-zA-Z0-9_\-\/]+$", name):
            raise ValueError("Invalid ZFS dataset name")

        if self.mock:
            if name in self._mock_zfs_datasets:
                self._mock_zfs_datasets.pop(name)
                # clear related snapshots
                self._mock_zfs_snapshots = {k: v for k, v in self._mock_zfs_snapshots.items() if not k.startswith(name + "@")}
                return True
            return False

        self._execute(["zfs", "destroy", "-r", name])
        return True

    def create_snapshot(self, dataset_or_volume: str, snapshot_name: str) -> dict:
        """Create a point-in-time snapshot."""
        full_snap_name = f"{dataset_or_volume}@{snapshot_name}"
        if not re.match(r"^[a-zA-Z0-9_\-\/\@]+$", full_snap_name):
            raise ValueError("Invalid ZFS snapshot name syntax")

        if self.mock:
            self._mock_zfs_snapshots[full_snap_name] = {
                "name": full_snap_name,
                "dataset": dataset_or_volume,
                "snapshot": snapshot_name,
                "creation": "Just now",
                "used": "0B"
            }
            return self._mock_zfs_snapshots[full_snap_name]

        self._execute(["zfs", "snapshot", full_snap_name])
        return {
            "name": full_snap_name,
            "dataset": dataset_or_volume,
            "snapshot": snapshot_name,
            "creation": "Created",
            "used": "0B"
        }

    def get_snapshots(self) -> list:
        """List all ZFS snapshots."""
        if self.mock:
            for snap in self._mock_zfs_snapshots.values():
                if "holds" not in snap:
                    snap["holds"] = []
            return list(self._mock_zfs_snapshots.values())

        snapshots = []
        try:
            out = self._execute(["zfs", "list", "-t", "snapshot", "-H", "-o", "name,used,creation"])
            for line in out.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    name = parts[0]
                    dataset, snap = name.split("@")
                    
                    holds = []
                    try:
                        holds_out = self._execute(["zfs", "holds", "-H", name], check=False)
                        for h_line in holds_out.strip().split("\n"):
                            if h_line:
                                h_parts = h_line.split("\t")
                                if len(h_parts) >= 2:
                                    holds.append(h_parts[1].strip())
                    except Exception:
                        pass

                    snapshots.append({
                        "name": name,
                        "dataset": dataset,
                        "snapshot": snap,
                        "creation": parts[2],
                        "used": parts[1],
                        "holds": holds
                    })
        except Exception as e:
            logger.error(f"Failed to query ZFS snapshots: {e}")

        return snapshots

    def rollback_snapshot(self, snapshot_full_name: str) -> bool:
        """Rollback dataset to snapshot."""
        if "@" not in snapshot_full_name or not re.match(r"^[a-zA-Z0-9_\-\/\@]+$", snapshot_full_name):
            raise ValueError("Invalid snapshot name structure")

        if self.mock:
            return snapshot_full_name in self._mock_zfs_snapshots

        self._execute(["zfs", "rollback", "-r", snapshot_full_name])
        return True

    def destroy_snapshot(self, snapshot_full_name: str) -> bool:
        """Destroy a snapshot."""
        if "@" not in snapshot_full_name or not re.match(r"^[a-zA-Z0-9_\-\/\@]+$", snapshot_full_name):
            raise ValueError("Invalid snapshot name structure")

        if self.mock:
            if snapshot_full_name in self._mock_zfs_snapshots:
                self._mock_zfs_snapshots.pop(snapshot_full_name)
                return True
            return False

        self._execute(["zfs", "destroy", snapshot_full_name])
        return True

    def hold_snapshot(self, snapshot: str, tag: str) -> bool:
        """Hold snapshot to prevent deletion."""
        if not re.match(r"^[a-zA-Z0-9_\-\/\@]+$", snapshot) or not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
            raise ValueError("Invalid snapshot or tag syntax")
        
        if self.mock:
            if snapshot in self._mock_zfs_snapshots:
                if "holds" not in self._mock_zfs_snapshots[snapshot]:
                    self._mock_zfs_snapshots[snapshot]["holds"] = []
                if tag not in self._mock_zfs_snapshots[snapshot]["holds"]:
                    self._mock_zfs_snapshots[snapshot]["holds"].append(tag)
                return True
            return False

        self._execute(["zfs", "hold", tag, snapshot])
        return True

    def release_snapshot(self, snapshot: str, tag: str) -> bool:
        """Release a hold on a snapshot."""
        if not re.match(r"^[a-zA-Z0-9_\-\/\@]+$", snapshot) or not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
            raise ValueError("Invalid snapshot or tag syntax")

        if self.mock:
            if snapshot in self._mock_zfs_snapshots:
                if "holds" in self._mock_zfs_snapshots[snapshot]:
                    self._mock_zfs_snapshots[snapshot]["holds"] = [h for h in self._mock_zfs_snapshots[snapshot]["holds"] if h != tag]
                return True
            return False

        self._execute(["zfs", "release", tag, snapshot])
        return True

    def encrypt_device(self, path: str, passphrase: str) -> bool:
        """LUKS format a block device."""
        if not re.match(r"^[a-zA-Z0-9_\-\/]+$", path):
            raise ValueError("Invalid path format")

        if self.mock:
            disk_name = os.path.basename(path)
            found = False
            for d in self._mock_disks:
                if d["name"] == disk_name:
                    d["fstype"] = "crypto_LUKS"
                    d["mountpoint"] = "LUKS_LOCKED"
                    found = True
            if not found:
                for k, arr in self._mock_mdadm_arrays.items():
                    if k == disk_name or f"/dev/{k}" == path:
                        arr["fstype"] = "crypto_LUKS"
                        arr["mountpoint"] = "LUKS_LOCKED"
                        found = True
            if not found:
                zvol_suffix = path.replace("/dev/", "")
                if zvol_suffix.startswith("zvol/"):
                    zvol_suffix = zvol_suffix.replace("zvol/", "")
                for k, zvol in self._mock_zvols.items():
                    if k == zvol_suffix or zvol["name"] == disk_name:
                        zvol["fstype"] = "crypto_LUKS"
                        zvol["mountpoint"] = "LUKS_LOCKED"
                        found = True
            return True

        cmd = ["cryptsetup", "luksFormat", "--batch-mode", path]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = p.communicate(input=passphrase)
        if p.returncode != 0:
            raise Exception(f"LUKS Format failed: {stderr}")
        return True

    def open_encrypted_device(self, path: str, name: str, passphrase: str) -> str:
        """Unlock LUKS encrypted device to /dev/mapper/<name>."""
        if not re.match(r"^[a-zA-Z0-9_\-\/]+$", path) or not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid path or mapper name syntax")

        if self.mock:
            disk_name = os.path.basename(path)
            found = False
            for d in self._mock_disks:
                if d["name"] == disk_name:
                    d["fstype"] = "ext4"
                    d["mountpoint"] = f"/dev/mapper/{name}"
                    found = True
            if not found:
                for k, arr in self._mock_mdadm_arrays.items():
                    if k == disk_name or f"/dev/{k}" == path:
                        arr["fstype"] = "ext4"
                        arr["mountpoint"] = f"/dev/mapper/{name}"
                        found = True
            if not found:
                zvol_suffix = path.replace("/dev/", "")
                if zvol_suffix.startswith("zvol/"):
                    zvol_suffix = zvol_suffix.replace("zvol/", "")
                for k, zvol in self._mock_zvols.items():
                    if k == zvol_suffix or zvol["name"] == disk_name:
                        zvol["fstype"] = "ext4"
                        zvol["mountpoint"] = f"/dev/mapper/{name}"
                        found = True
            return f"/dev/mapper/{name}"

        cmd = ["cryptsetup", "open", path, name]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = p.communicate(input=passphrase)
        if p.returncode != 0:
            raise Exception(f"LUKS Open failed: {stderr}")
        return f"/dev/mapper/{name}"

    def close_encrypted_device(self, name: str) -> bool:
        """Lock LUKS mapper target."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid mapper name syntax")

        if self.mock:
            mapper = f"/dev/mapper/{name}"
            for d in self._mock_disks:
                if d["mountpoint"] == mapper:
                    d["fstype"] = "crypto_LUKS"
                    d["mountpoint"] = "LUKS_LOCKED"
            for arr in self._mock_mdadm_arrays.values():
                if arr["mountpoint"] == mapper:
                    arr["fstype"] = "crypto_LUKS"
                    arr["mountpoint"] = "LUKS_LOCKED"
            for zvol in self._mock_zvols.values():
                if zvol["mountpoint"] == mapper:
                    zvol["fstype"] = "crypto_LUKS"
                    zvol["mountpoint"] = "LUKS_LOCKED"
            return True

        self._execute(["cryptsetup", "close", name])
        return True

    def create_zvol(self, pool: str, name: str, size_gb: int) -> dict:
        """Create a ZFS Volume (Zvol)."""
        fullname = f"{pool}/{name}"
        if not re.match(r"^[a-zA-Z0-9_\-]+$", pool) or not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ValueError("Invalid pool or zvol name structure")
        if size_gb <= 0:
            raise ValueError("Size must be greater than 0")

        if self.mock:
            self._mock_zvols[fullname] = {
                "name": name,
                "pool": pool,
                "fullname": fullname,
                "size_gb": size_gb,
                "mountpoint": None,
                "fstype": None
            }
            return self._mock_zvols[fullname]

        self._execute(["zfs", "create", "-V", f"{size_gb}G", fullname])
        return {
            "name": name,
            "pool": pool,
            "fullname": fullname,
            "size_gb": size_gb,
            "mountpoint": None,
            "fstype": None
        }

    def get_zvols(self) -> list:
        """List ZFS volumes (Zvols)."""
        if self.mock:
            return list(self._mock_zvols.values())

        zvols = []
        try:
            out = self._execute(["zfs", "list", "-t", "volume", "-H", "-o", "name,volsize"])
            for line in out.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    fullname = parts[0]
                    pool, name = fullname.split("/", 1)
                    # Convert ZFS volsize (e.g. 50G) to size_gb
                    zvols.append({
                        "name": name,
                        "pool": pool,
                        "fullname": fullname,
                        "size_gb": parts[1].replace("G", ""),
                        "mountpoint": None,
                        "fstype": None
                    })
        except Exception as e:
            logger.error(f"Failed to query Zvols: {e}")

        return zvols

    def destroy_zvol(self, pool: str, name: str) -> bool:
        """Destroy a Zvol."""
        fullname = f"{pool}/{name}"
        if self.mock:
            if fullname in self._mock_zvols:
                self._mock_zvols.pop(fullname)
                return True
            return False

        self._execute(["zfs", "destroy", fullname])
        return True
