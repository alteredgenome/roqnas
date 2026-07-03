import os
import sys
import socket
import pty
import fcntl
import struct
import termios
import select
import subprocess
import json
import logging
import asyncio
import re
import jwt
import datetime
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import psutil

# Add local path to import storage
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from storage import StorageManager
from security import SecurityManager
from directory import DirectoryManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("roqnas.main")

# Configuration
JWT_SECRET = os.getenv("ROQNAS_JWT_SECRET", os.getenv("ROCKNAS_JWT_SECRET", "roqnas_super_secret_key_1337"))
JWT_ALGORITHM = "HS256"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
CONFIG_DIR = "/etc/roqnas"
try:
    os.makedirs(CONFIG_DIR, exist_ok=True)
except PermissionError:
    CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    os.makedirs(CONFIG_DIR, exist_ok=True)

MOCK_MODE = "--mock" in sys.argv or os.getenv("ROQNAS_MOCK", os.getenv("ROCKNAS_MOCK", "true")).lower() == "true"
storage_manager = StorageManager(mock=MOCK_MODE)
security_manager = SecurityManager(mock=MOCK_MODE)
directory_manager = DirectoryManager(mock=MOCK_MODE)

def ensure_samba_global_settings():
    if MOCK_MODE:
        return
    smb_conf = "/etc/samba/smb.conf"
    if not os.path.exists(smb_conf):
        return
    try:
        with open(smb_conf, "r") as f:
            content = f.read()
        
        # Check if fruit settings are already configured
        if "fruit:metadata" not in content:
            logger.info("Injecting Apple vfs_fruit compatibility layers into Samba global section...")
            apple_settings = (
                "\n   # Apple vfs_fruit compatibility settings\n"
                "   vfs objects = catia fruit streams_xattr\n"
                "   fruit:metadata = netatalk\n"
                "   fruit:veto_appledouble = no\n"
                "   fruit:posix_rename = yes\n"
            )
            # Insert right after [global]
            updated = re.sub(r"\[global\]", f"[global]{apple_settings}", content, count=1)
            with open(smb_conf, "w") as f:
                f.write(updated)
            subprocess.run(["systemctl", "restart", "smbd"], check=False)
    except Exception as e:
        logger.error(f"Failed ensuring Samba global settings: {e}")

ensure_samba_global_settings()

app = FastAPI(title="RoqNAS Engine", description="Unified System Control Plane for RoqNAS OS")

@app.on_event("startup")
def on_startup():
    try:
        cfg = load_mdns_config()
        generate_avahi_services(cfg["active"], cfg["model"])
    except Exception as e:
        logger.error(f"Failed loading mDNS configurations on startup: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

security = HTTPBearer()

# Helper for system users DB
def load_users() -> dict:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}

def save_users(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Create default admin user if none exists
users_db = load_users()
if not users_db.get("users"):
    users_db["users"]["admin"] = {
        "password": "admin", # Default password, user should change this
        "role": "admin",
        "email": "admin@rocknas.local",
        "created_at": str(datetime.datetime.utcnow())
    }
    save_users(users_db)

# Dependency to check auth
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token has expired or is invalid")

# API Models
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "standard" # admin, standard
    email: Optional[str] = ""

class NetworkConfigUpdate(BaseModel):
    interface: str
    dhcp: bool
    address: Optional[str] = ""
    gateway: Optional[str] = ""
    dns: Optional[List[str]] = []
    mtu: Optional[int] = 1500

class SMBSignedShare(BaseModel):
    name: str
    path: str
    read_only: bool = False
    guest_ok: bool = True
    comment: Optional[str] = ""
    time_machine: Optional[bool] = False
    time_machine_max_size: Optional[str] = ""

class NFSSignedShare(BaseModel):
    path: str
    allowed_hosts: str = "*"
    options: str = "rw,sync,no_subtree_check,no_root_squash"

class ISCSITarget(BaseModel):
    target_iqn: str
    backing_store: str # Device or file path
    initiator_address: Optional[str] = "ALL"

class VMCreation(BaseModel):
    name: str
    ram_mb: int = 1024
    vcpu: int = 1
    disk_gb: int = 10
    iso_path: Optional[str] = ""

# Authentication
@app.post("/api/auth/login")
def login(req: LoginRequest):
    db = load_users()
    user = db["users"].get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Check if MFA is active
    if user.get("mfa_enabled", False):
        challenge_token = jwt.encode({
            "sub": req.username,
            "mfa_challenge": True,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        }, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"mfa_required": True, "challenge_token": challenge_token}

    token = jwt.encode({
        "sub": req.username,
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {"token": token, "username": req.username, "role": user["role"]}

class LoginMfaRequest(BaseModel):
    challenge_token: str
    code: str

@app.post("/api/auth/login/mfa")
def login_mfa(req: LoginMfaRequest):
    try:
        payload = jwt.decode(req.challenge_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if not payload.get("mfa_challenge"):
            raise HTTPException(status_code=400, detail="Invalid challenge token")
        username = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Challenge token expired or invalid")

    db = load_users()
    user = db["users"].get(username)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    secret = user.get("mfa_secret")
    if not secret or not security_manager.verify_totp(secret, req.code):
        raise HTTPException(status_code=400, detail="Incorrect authentication token")

    token = jwt.encode({
        "sub": username,
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {"token": token, "username": username, "role": user["role"]}

# MFA Management setup and verify
class MfaVerifyRequest(BaseModel):
    secret: str
    code: str
    enable: bool = True

@app.post("/api/auth/mfa/setup", dependencies=[Depends(get_current_user)])
def setup_mfa(username: str = Depends(get_current_user)):
    secret = security_manager.generate_totp_secret()
    otpauth_url = f"otpauth://totp/RockNAS:{username}?secret={secret}&issuer=RockNAS"
    return {"secret": secret, "otpauth_url": otpauth_url}

@app.post("/api/auth/mfa/verify", dependencies=[Depends(get_current_user)])
def verify_mfa(req: MfaVerifyRequest, username: str = Depends(get_current_user)):
    if not security_manager.verify_totp(req.secret, req.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    db = load_users()
    user = db["users"].get(username)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if req.enable:
        user["mfa_secret"] = req.secret
        user["mfa_enabled"] = True
    else:
        user["mfa_secret"] = None
        user["mfa_enabled"] = False

    save_users(db)
    return {"message": "MFA configuration saved successfully.", "enabled": req.enable}

# Fail2ban Endpoints
class Fail2banConfigReq(BaseModel):
    bantime: int
    maxretry: int

class UnbanReq(BaseModel):
    jail: str
    ip: str

@app.get("/api/security/fail2ban/status", dependencies=[Depends(get_current_user)])
def get_fail2ban_status():
    return security_manager.get_fail2ban_status()

@app.post("/api/security/fail2ban/unban", dependencies=[Depends(get_current_user)])
def unban_ip(req: UnbanReq):
    try:
        security_manager.unban_ip(req.jail, req.ip)
        return {"message": f"IP {req.ip} unbanned from jail {req.jail}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/security/fail2ban/config", dependencies=[Depends(get_current_user)])
def configure_fail2ban(req: Fail2banConfigReq):
    try:
        security_manager.update_fail2ban_config(req.bantime, req.maxretry)
        return {"message": "Fail2ban jail configuration updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Security Counselor Endpoints
counselor_state = {
    "scanning": False,
    "last_run": "-",
    "results": []
}

async def run_async_counselor_scan():
    global counselor_state
    counselor_state["scanning"] = True
    counselor_state["results"] = []
    # run sweep
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, security_manager.execute_counselor_scan)
    counselor_state["results"] = results
    counselor_state["scanning"] = False
    counselor_state["last_run"] = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.post("/api/security/counselor/scan", dependencies=[Depends(get_current_user)])
async def trigger_counselor_scan():
    global counselor_state
    if counselor_state["scanning"]:
        return {"message": "Scan already in progress."}
    asyncio.create_task(run_async_counselor_scan())
    return {"message": "Security scan launched in background."}

@app.get("/api/security/counselor/results", dependencies=[Depends(get_current_user)])
def get_counselor_results():
    return counselor_state

# Models for v0.0.5 additions
class AdJoinRequest(BaseModel):
    domain: str
    username: str
    password: str
    dns_ip: str

class LdapConfigRequest(BaseModel):
    server: str
    base_dn: str
    bind_dn: str
    password: str

class SsoConfigRequest(BaseModel):
    enabled: bool
    provider: str
    metadata_url: str
    client_id: str
    client_secret: str

@app.get("/api/directory/ad", dependencies=[Depends(get_current_user)])
def get_ad_status():
    return directory_manager.get_ad_status()

@app.post("/api/directory/ad/join", dependencies=[Depends(get_current_user)])
def join_ad_domain(req: AdJoinRequest):
    try:
        directory_manager.join_ad_domain(req.domain, req.username, req.password, req.dns_ip)
        return {"message": f"Successfully joined domain {req.domain}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/directory/ad/leave", dependencies=[Depends(get_current_user)])
def leave_ad_domain():
    try:
        directory_manager.leave_ad_domain()
        return {"message": "Successfully left domain."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/directory/ldap", dependencies=[Depends(get_current_user)])
def get_ldap_status():
    return directory_manager.get_ldap_status()

@app.post("/api/directory/ldap/config", dependencies=[Depends(get_current_user)])
def configure_ldap(req: LdapConfigRequest):
    try:
        directory_manager.configure_ldap_client(req.server, req.base_dn, req.bind_dn, req.password)
        return {"message": "LDAP Client config updated and lookup daemon restarted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/directory/sso", dependencies=[Depends(get_current_user)])
def get_sso_status():
    return directory_manager.get_sso_status()

@app.post("/api/directory/sso/config", dependencies=[Depends(get_current_user)])
def configure_sso(req: SsoConfigRequest):
    try:
        directory_manager.configure_sso(req.enabled, req.provider, req.metadata_url, req.client_id, req.client_secret)
        return {"message": "Single Sign-On settings updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Users Module
@app.get("/api/users", dependencies=[Depends(get_current_user)])
def list_users():
    db = load_users()
    users = []
    for uname, udata in db["users"].items():
        users.append({
            "username": uname,
            "role": udata.get("role", "standard"),
            "email": udata.get("email", ""),
            "created_at": udata.get("created_at", ""),
            "mfa_enabled": udata.get("mfa_enabled", False)
        })
    return users

@app.post("/api/users", dependencies=[Depends(get_current_user)])
def create_user(req: UserCreate):
    db = load_users()
    if req.username in db["users"]:
        raise HTTPException(status_code=400, detail="User already exists")
    db["users"][req.username] = {
        "password": req.password,
        "role": req.role,
        "email": req.email,
        "created_at": str(datetime.datetime.utcnow())
    }
    save_users(db)
    # Sync with system user if not in mock mode
    if not MOCK_MODE:
        try:
            subprocess.run(["useradd", "-m", "-s", "/bin/false", req.username], check=False)
            p1 = subprocess.Popen(["echo", f"{req.password}"], stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["chpasswd"], stdin=p1.stdout, stdout=subprocess.PIPE)
            p1.stdout.close()
            p2.communicate()
            
            # Sync smbpasswd
            smb_p1 = subprocess.Popen(["echo", f"{req.password}\n{req.password}"], stdout=subprocess.PIPE)
            subprocess.run(["smbpasswd", "-s", "-a", req.username], stdin=smb_p1.stdout, check=False)
        except Exception as e:
            logger.error(f"Failed to sync system user: {e}")
    return {"message": "User created successfully"}

@app.delete("/api/users/{username}", dependencies=[Depends(get_current_user)])
def delete_user(username: str):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super admin")
    db = load_users()
    if username in db["users"]:
        db["users"].pop(username)
        save_users(db)
        if not MOCK_MODE:
            try:
                subprocess.run(["userdel", "-r", username], check=False)
            except Exception:
                pass
        return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")

# Core Networking
@app.get("/api/network/interfaces", dependencies=[Depends(get_current_user)])
def get_network_interfaces():
    if MOCK_MODE:
        return [
            {"name": "eth0", "ip": "192.168.1.100", "netmask": "255.255.255.0", "gateway": "192.168.1.1", "mtu": 1500, "status": "UP", "dhcp": True},
            {"name": "eth1", "ip": "", "netmask": "", "gateway": "", "mtu": 9000, "status": "DOWN", "dhcp": False}
        ]

    interfaces = []
    for name, stats in psutil.net_if_stats().items():
        addrs = psutil.net_if_addrs().get(name, [])
        ip = ""
        netmask = ""
        for addr in addrs:
            if addr.family == 2: # IPv4
                ip = addr.address
                netmask = addr.netmask
                break
        
        # Check gateway
        gateway = ""
        try:
            route_out = subprocess.run(["ip", "route", "show", "default"], stdout=subprocess.PIPE, text=True)
            match = re.search(r"default via ([\d\.]+) dev", route_out.stdout)
            if match:
                gateway = match.group(1)
        except Exception:
            pass

        interfaces.append({
            "name": name,
            "ip": ip,
            "netmask": netmask,
            "gateway": gateway,
            "mtu": stats.mtu,
            "status": "UP" if stats.isup else "DOWN",
            "dhcp": True # Simple default
        })
    return interfaces

@app.post("/api/network/configure", dependencies=[Depends(get_current_user)])
def configure_network(req: NetworkConfigUpdate):
    if not re.match(r"^[a-zA-Z0-9_\-]+$", req.interface):
        raise HTTPException(status_code=400, detail="Invalid interface name")

    if MOCK_MODE:
        return {"message": f"Interface {req.interface} configured successfully (MOCKED)"}

    # Generate systemd-networkd config file
    config_path = f"/etc/systemd/network/10-{req.interface}.network"
    config_data = f"[Match]\nName={req.interface}\n\n[Network]\n"
    if req.dhcp:
        config_data += "DHCP=yes\n"
    else:
        config_data += f"Address={req.address}\n"
        if req.gateway:
            config_data += f"Gateway={req.gateway}\n"
        for dns_ip in req.dns:
            if dns_ip:
                config_data += f"DNS={dns_ip}\n"
    
    config_data += f"\n[Link]\nMTUBytes={req.mtu}\n"

    try:
        with open(config_path, "w") as f:
            f.write(config_data)
        
        # Apply changes via systemctl
        subprocess.run(["systemctl", "restart", "systemd-networkd"], check=True)
        return {"message": f"Interface {req.interface} updated and systemd-networkd restarted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply network configuration: {e}")

# Storage Routing
@app.get("/api/storage/disks", dependencies=[Depends(get_current_user)])
def list_disks():
    return storage_manager.get_block_devices()

@app.get("/api/storage/mdadm", dependencies=[Depends(get_current_user)])
def list_mdadm_arrays():
    return storage_manager.get_mdadm_arrays()

@app.post("/api/storage/mdadm", dependencies=[Depends(get_current_user)])
def create_mdadm(name: str, level: int, disks: List[str], fstype: str = "ext4"):
    try:
        return storage_manager.create_mdadm_array(name, level, disks, fstype)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/storage/mdadm/{name}", dependencies=[Depends(get_current_user)])
def destroy_mdadm(name: str):
    try:
        storage_manager.remove_mdadm_array(name)
        return {"message": f"mdadm array {name} destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# MDADM disk management / growth
@app.post("/api/storage/mdadm/{name}/add-disk", dependencies=[Depends(get_current_user)])
def add_mdadm_disk(name: str, disk: str):
    try:
        storage_manager.add_mdadm_disk(name, disk)
        return {"message": f"Disk {disk} added to array {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/mdadm/{name}/grow", dependencies=[Depends(get_current_user)])
def grow_mdadm_array(name: str, new_num_devices: int):
    try:
        storage_manager.grow_mdadm_array(name, new_num_devices)
        return {"message": f"Array {name} grown to {new_num_devices} devices."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/mdadm/{name}/fail-disk", dependencies=[Depends(get_current_user)])
def fail_mdadm_disk(name: str, disk: str):
    try:
        storage_manager.fail_mdadm_disk(name, disk)
        return {"message": f"Disk {disk} marked as failed in array {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/mdadm/{name}/remove-disk", dependencies=[Depends(get_current_user)])
def remove_mdadm_disk(name: str, disk: str):
    try:
        storage_manager.remove_mdadm_disk(name, disk)
        return {"message": f"Disk {disk} removed from array {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/storage/zpool", dependencies=[Depends(get_current_user)])
def list_zpools():
    return storage_manager.get_zpools()

@app.post("/api/storage/zpool", dependencies=[Depends(get_current_user)])
def create_zpool(name: str, layout: str, disks: List[str]):
    try:
        return storage_manager.create_zpool(name, layout, disks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/storage/zpool/{name}", dependencies=[Depends(get_current_user)])
def destroy_zpool(name: str):
    try:
        storage_manager.destroy_zpool(name)
        return {"message": f"zpool {name} destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Zpool growth / expansion / replacement
@app.post("/api/storage/zpool/{name}/expand-vdev", dependencies=[Depends(get_current_user)])
def expand_zpool_vdev(name: str, layout: str, disks: List[str]):
    try:
        storage_manager.add_zpool_vdev(name, layout, disks)
        return {"message": f"vdev successfully attached to pool {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/zpool/{name}/replace-disk", dependencies=[Depends(get_current_user)])
def replace_zpool_disk(name: str, old_disk: str, new_disk: str):
    try:
        storage_manager.replace_zpool_disk(name, old_disk, new_disk)
        return {"message": f"Disk replacement initiated in pool {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/zpool/{name}/expand-raidz", dependencies=[Depends(get_current_user)])
def expand_zpool_raidz(name: str, vdev: str, new_disk: str):
    try:
        storage_manager.expand_raidz(name, vdev, new_disk)
        return {"message": f"RAIDZ expansion triggered for vdev {vdev} in pool {name}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/storage/zfs/datasets", dependencies=[Depends(get_current_user)])
def list_zfs_datasets():
    return storage_manager.get_zfs_datasets()

@app.post("/api/storage/zfs/datasets", dependencies=[Depends(get_current_user)])
def create_zfs_dataset(pool: str, name: str):
    try:
        return storage_manager.create_zfs_dataset(pool, name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/storage/zfs/datasets/{name:path}", dependencies=[Depends(get_current_user)])
def destroy_zfs_dataset(name: str):
    try:
        storage_manager.destroy_zfs_dataset(name)
        return {"message": f"ZFS dataset {name} destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Snapshots Routing
@app.get("/api/storage/zfs/snapshots", dependencies=[Depends(get_current_user)])
def list_zfs_snapshots():
    return storage_manager.get_snapshots()

@app.post("/api/storage/zfs/snapshots", dependencies=[Depends(get_current_user)])
def create_zfs_snapshot(dataset: str, name: str):
    try:
        return storage_manager.create_snapshot(dataset, name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/zfs/snapshots/rollback", dependencies=[Depends(get_current_user)])
def rollback_zfs_snapshot(snapshot: str):
    try:
        storage_manager.rollback_snapshot(snapshot)
        return {"message": f"Rolled back to {snapshot} successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Models for v0.0.3 additions
class SnapshotHoldConfig(BaseModel):
    snapshot: str
    tag: str

class LuksFormatConfig(BaseModel):
    path: str
    passphrase: str

class LuksOpenConfig(BaseModel):
    path: str
    name: str
    passphrase: str

class LuksCloseConfig(BaseModel):
    name: str

class CloudSyncConfig(BaseModel):
    name: str
    local_path: str
    provider: str
    bucket: str
    schedule: str
    access_key: Optional[str] = ""
    secret_key: Optional[str] = ""

# In-memory mock cloud sync tasks db
mock_sync_tasks = {
    "1": {
        "id": "1",
        "name": "S3 Media Backup",
        "local_path": "/tank/media",
        "provider": "AWS S3",
        "bucket": "rocknas-media-archive",
        "schedule": "0 2 * * *",
        "status": "idle",
        "progress": 0,
        "last_run": "2026-07-02 02:00:05"
    }
}

# Cloud Sync Endpoints
@app.get("/api/backup/cloud", dependencies=[Depends(get_current_user)])
def get_cloud_sync_tasks():
    return list(mock_sync_tasks.values())

@app.post("/api/backup/cloud", dependencies=[Depends(get_current_user)])
def create_cloud_sync_task(req: CloudSyncConfig):
    new_id = str(len(mock_sync_tasks) + 1)
    mock_sync_tasks[new_id] = {
        "id": new_id,
        "name": req.name,
        "local_path": req.local_path,
        "provider": req.provider,
        "bucket": req.bucket,
        "schedule": req.schedule,
        "status": "idle",
        "progress": 0,
        "last_run": "-"
    }
    return {"message": "Cloud sync task created successfully.", "id": new_id}

@app.delete("/api/backup/cloud/{task_id}", dependencies=[Depends(get_current_user)])
def delete_cloud_sync_task(task_id: str):
    if task_id in mock_sync_tasks:
        mock_sync_tasks.pop(task_id)
        return {"message": "Cloud sync task deleted successfully."}
    raise HTTPException(status_code=404, detail="Task not found")

async def run_simulated_sync(task_id: str):
    if task_id not in mock_sync_tasks:
        return
    task = mock_sync_tasks[task_id]
    task["status"] = "syncing"
    task["progress"] = 0
    for i in range(1, 11):
        await asyncio.sleep(0.5)
        task["progress"] = i * 10
    task["status"] = "success"
    task["last_run"] = str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.post("/api/backup/cloud/{task_id}/sync-run", dependencies=[Depends(get_current_user)])
async def trigger_cloud_sync_run(task_id: str):
    # Run async background task
    asyncio.create_task(run_simulated_sync(task_id))
    return {"message": "Synchronisation launched in background."}

# LUKS Endpoints
@app.post("/api/storage/luks/encrypt", dependencies=[Depends(get_current_user)])
def encrypt_disk(req: LuksFormatConfig):
    try:
        storage_manager.encrypt_device(req.path, req.passphrase)
        return {"message": f"Device {req.path} successfully formatted with LUKS encryption."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/luks/open", dependencies=[Depends(get_current_user)])
def open_disk(req: LuksOpenConfig):
    try:
        mapper_path = storage_manager.open_encrypted_device(req.path, req.name, req.passphrase)
        return {"message": f"Device {req.path} unlocked. Mapper target: {mapper_path}", "mapper": mapper_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/luks/close", dependencies=[Depends(get_current_user)])
def close_disk(req: LuksCloseConfig):
    try:
        storage_manager.close_encrypted_device(req.name)
        return {"message": f"Mapper target {req.name} closed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ZFS Snapshot Hold locks
@app.post("/api/storage/zfs/snapshots/hold", dependencies=[Depends(get_current_user)])
def hold_snapshot(req: SnapshotHoldConfig):
    try:
        storage_manager.hold_snapshot(req.snapshot, req.tag)
        return {"message": f"Hold lock '{req.tag}' applied on snapshot {req.snapshot}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/zfs/snapshots/release", dependencies=[Depends(get_current_user)])
def release_snapshot(req: SnapshotHoldConfig):
    try:
        storage_manager.release_snapshot(req.snapshot, req.tag)
        return {"message": f"Hold lock '{req.tag}' released from snapshot {req.snapshot}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/storage/zfs/snapshots/{snapshot:path}", dependencies=[Depends(get_current_user)])
def destroy_zfs_snapshot(snapshot: str):
    try:
        # Check holds before deleting
        snaps = storage_manager.get_snapshots()
        target = next((s for s in snaps if s["name"] == snapshot), None)
        if target and target.get("holds"):
            raise HTTPException(status_code=400, detail=f"Cannot delete snapshot: locked by active holds {target['holds']}")

        storage_manager.destroy_snapshot(snapshot)
        return {"message": f"Snapshot {snapshot} destroyed."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ZvolCreateConfig(BaseModel):
    pool: str
    name: str
    size_gb: int

@app.get("/api/storage/zfs/zvol", dependencies=[Depends(get_current_user)])
def list_zvols():
    try:
        return storage_manager.get_zvols()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/storage/zfs/zvol", dependencies=[Depends(get_current_user)])
def create_zvol(req: ZvolCreateConfig):
    try:
        zvol = storage_manager.create_zvol(req.pool, req.name, req.size_gb)
        return {"message": f"ZFS block volume {req.pool}/{req.name} created.", "zvol": zvol}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/storage/zfs/zvol/{pool}/{name}", dependencies=[Depends(get_current_user)])
def destroy_zvol(pool: str, name: str):
    try:
        storage_manager.destroy_zvol(pool, name)
        return {"message": f"ZFS block volume {pool}/{name} destroyed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SMB / NFS Exports
@app.get("/api/shares/smb", dependencies=[Depends(get_current_user)])
def list_smb_shares():
    if MOCK_MODE:
        return [
            {"name": "BackupShare", "path": "/mnt/md0/backups", "read_only": False, "guest_ok": True, "comment": "MOCK Storage Array backup", "time_machine": True, "time_machine_max_size": "500G"},
            {"name": "MediaPool", "path": "/tank/media", "read_only": True, "guest_ok": True, "comment": "MOCK ZFS Media pool", "time_machine": False, "time_machine_max_size": ""}
        ]

    # Parse /etc/samba/smb.conf
    shares = []
    if not os.path.exists("/etc/samba/smb.conf"):
        return shares

    with open("/etc/samba/smb.conf", "r") as f:
        content = f.read()

    # Regex block parser
    blocks = re.findall(r"\[([^\]]+)\]\n([^\[]*)", content, re.MULTILINE)
    for title, body in blocks:
        if title in ["global", "homes", "printers", "print$"]:
            continue
        
        path_match = re.search(r"path\s*=\s*(.+)", body)
        ro_match = re.search(r"read only\s*=\s*(.+)", body)
        guest_match = re.search(r"guest ok\s*=\s*(.+)", body)
        comment_match = re.search(r"comment\s*=\s*(.+)", body)
        tm_match = re.search(r"fruit:time machine\s*=\s*(.+)", body)
        tm_size_match = re.search(r"fruit:time machine max size\s*=\s*(.+)", body)

        shares.append({
            "name": title.strip(),
            "path": path_match.group(1).strip() if path_match else "",
            "read_only": ro_match.group(1).strip().lower() in ["yes", "true"] if ro_match else False,
            "guest_ok": guest_match.group(1).strip().lower() in ["yes", "true"] if guest_match else True,
            "comment": comment_match.group(1).strip() if comment_match else "",
            "time_machine": tm_match.group(1).strip().lower() in ["yes", "true"] if tm_match else False,
            "time_machine_max_size": tm_size_match.group(1).strip() if tm_size_match else ""
        })

    return shares

@app.post("/api/shares/smb", dependencies=[Depends(get_current_user)])
def add_smb_share(req: SMBSignedShare):
    if not re.match(r"^[a-zA-Z0-9_\-]+$", req.name):
        raise HTTPException(status_code=400, detail="Invalid share name")

    if MOCK_MODE:
        return {"message": "Share added successfully (MOCKED)"}

    # Append to /etc/samba/smb.conf
    block = f"\n[{req.name}]\n"
    block += f"   path = {req.path}\n"
    block += f"   read only = {'yes' if req.read_only else 'no'}\n"
    block += f"   guest ok = {'yes' if req.guest_ok else 'no'}\n"
    block += f"   comment = {req.comment}\n"
    block += "   browseable = yes\n"
    block += "   create mask = 0775\n"
    block += "   directory mask = 0775\n"
    if req.time_machine:
        block += "   fruit:time machine = yes\n"
        if req.time_machine_max_size:
            block += f"   fruit:time machine max size = {req.time_machine_max_size}\n"

    try:
        os.makedirs(req.path, exist_ok=True)
        # Give appropriate perm
        subprocess.run(["chmod", "777", req.path], check=False)

        with open("/etc/samba/smb.conf", "a") as f:
            f.write(block)
        
        # restart samba
        subprocess.run(["systemctl", "restart", "smbd"], check=True)
        return {"message": f"Samba share {req.name} successfully deployed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/shares/nfs", dependencies=[Depends(get_current_user)])
def list_nfs_shares():
    if MOCK_MODE:
        return [
            {"path": "/tank/media", "allowed_hosts": "*", "options": "ro,sync,no_subtree_check"},
            {"path": "/mnt/md0/backups", "allowed_hosts": "192.168.1.0/24", "options": "rw,sync,no_root_squash"}
        ]

    shares = []
    if not os.path.exists("/etc/exports"):
        return shares

    with open("/etc/exports", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # format: /path/to/dir client1(options)
            match = re.match(r"^([^\s]+)\s+([^\(]+)\(([^\]]+)\)", line)
            if not match:
                # simple split fallback
                parts = line.split()
                if len(parts) >= 2:
                    shares.append({"path": parts[0], "allowed_hosts": parts[1], "options": "rw,sync"})
                continue
            
            shares.append({
                "path": match.group(1),
                "allowed_hosts": match.group(2),
                "options": match.group(3)
            })
    return shares

@app.post("/api/shares/nfs", dependencies=[Depends(get_current_user)])
def add_nfs_share(req: NFSSignedShare):
    if MOCK_MODE:
        return {"message": "NFS export added successfully (MOCKED)"}

    line = f"\n{req.path} {req.allowed_hosts}({req.options})\n"

    try:
        os.makedirs(req.path, exist_ok=True)
        with open("/etc/exports", "a") as f:
            f.write(line)
        subprocess.run(["exportfs", "-arv"], check=True)
        # restart NFS server
        subprocess.run(["systemctl", "restart", "nfs-kernel-server"], check=False)
        return {"message": f"NFS share for {req.path} exported."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# iSCSI Targets
@app.get("/api/iscsi/targets", dependencies=[Depends(get_current_user)])
def get_iscsi_targets():
    if MOCK_MODE:
        return [
            {"target_iqn": "iqn.2026-07.local.rocknas:lun1", "backing_store": "/dev/md0", "initiator_address": "ALL"}
        ]

    targets = []
    try:
        # read configurations under /etc/tgt/conf.d/
        # or call tgtadm
        tgt_dir = "/etc/tgt/conf.d"
        if os.path.exists(tgt_dir):
            for fname in os.listdir(tgt_dir):
                if fname.endswith(".conf"):
                    with open(os.path.join(tgt_dir, fname), "r") as f:
                        content = f.read()
                        iqn_match = re.search(r"<target\s+(iqn\.[^>]+)>", content)
                        backing_match = re.search(r"backing-store\s+(.+)", content)
                        init_match = re.search(r"initiator-address\s+(.+)", content)
                        if iqn_match:
                            targets.append({
                                "target_iqn": iqn_match.group(1).strip(),
                                "backing_store": backing_match.group(1).strip() if backing_match else "",
                                "initiator_address": init_match.group(1).strip() if init_match else "ALL"
                            })
    except Exception as e:
        logger.error(f"Failed parsing target configs: {e}")

    return targets

@app.post("/api/iscsi/targets", dependencies=[Depends(get_current_user)])
def add_iscsi_target(req: ISCSITarget):
    if not req.target_iqn.startswith("iqn."):
        raise HTTPException(status_code=400, detail="Target IQN must start with 'iqn.'")

    if MOCK_MODE:
        return {"message": "iSCSI target registered successfully (MOCKED)"}

    # Generate tgt conf file
    safe_name = req.target_iqn.replace(":", "_").replace(".", "_")
    conf_path = f"/etc/tgt/conf.d/rocknas_{safe_name}.conf"
    
    conf = f"<target {req.target_iqn}>\n"
    conf += f"    backing-store {req.backing_store}\n"
    if req.initiator_address and req.initiator_address != "ALL":
        conf += f"    initiator-address {req.initiator_address}\n"
    conf += "</target>\n"

    try:
        with open(conf_path, "w") as f:
            f.write(conf)
        subprocess.run(["systemctl", "restart", "tgt"], check=True)
        return {"message": f"iSCSI target {req.target_iqn} successfully created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Hypervisor Layer (libvirt VMs & LXC Containers)
@app.get("/api/hypervisor/vms", dependencies=[Depends(get_current_user)])
def get_virtual_machines():
    if MOCK_MODE:
        return [
            {"name": "Debian13-VM", "status": "running", "vcpu": 2, "ram_mb": 2048, "disk_gb": 40},
            {"name": "Nextcloud-LXC", "status": "stopped", "vcpu": 1, "ram_mb": 1024, "disk_gb": 20}
        ]

    vms = []
    try:
        import libvirt
        conn = libvirt.open("qemu:///system")
        if conn:
            # Active domains
            for domain_id in conn.listDomainsID():
                dom = conn.lookupByID(domain_id)
                info = dom.info()
                vms.append({
                    "name": dom.name(),
                    "status": "running",
                    "vcpu": info[3],
                    "ram_mb": int(info[1] / 1024),
                    "disk_gb": 0 # requires storage volumes parsing
                })
            
            # Inactive domains
            for dom_name in conn.listDefinedDomains():
                dom = conn.lookupByName(dom_name)
                info = dom.info()
                vms.append({
                    "name": dom_name,
                    "status": "stopped",
                    "vcpu": info[3],
                    "ram_mb": int(info[1] / 1024),
                    "disk_gb": 0
                })
            conn.close()
    except Exception as e:
        logger.error(f"libvirt exception: {e}")
        # fallback simple list
        vms = [{"name": "Debian-Fallback", "status": "unknown", "vcpu": 1, "ram_mb": 512, "disk_gb": 10}]
    return vms

@app.post("/api/hypervisor/vms", dependencies=[Depends(get_current_user)])
def create_virtual_machine(req: VMCreation):
    if not re.match(r"^[a-zA-Z0-9_\-]+$", req.name):
        raise HTTPException(status_code=400, detail="Invalid VM name")

    if MOCK_MODE:
        return {"message": f"VM {req.name} defined successfully (MOCKED)"}

    # Generate XML layout and define via libvirt
    xml = f"""
    <domain type='kvm'>
      <name>{req.name}</name>
      <memory unit='KiB'>{req.ram_mb * 1024}</memory>
      <currentMemory unit='KiB'>{req.ram_mb * 1024}</currentMemory>
      <vcpu placement='static'>{req.vcpu}</vcpu>
      <os>
        <type arch='x86_64' machine='pc-q35-8.0'>hvm</type>
        <boot dev='hd'/>
        {"<boot dev='cdrom'/>" if req.iso_path else ""}
      </os>
      <devices>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/{req.name}.qcow2'/>
          <target dev='vda' bus='virtio'/>
        </disk>
        {f'''
        <disk type='file' device='cdrom'>
          <driver name='qemu' type='raw'/>
          <source file='{req.iso_path}'/>
          <target dev='sda' bus='sata'/>
          <readonly/>
        </disk>
        ''' if req.iso_path else ""}
        <interface type='bridge'>
          <source bridge='virbr0'/>
          <model type='virtio'/>
        </interface>
        <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
      </devices>
    </domain>
    """

    try:
        # Create virtual disk
        disk_path = f"/var/lib/libvirt/images/{req.name}.qcow2"
        os.makedirs(os.path.dirname(disk_path), exist_ok=True)
        subprocess.run(["qemu-img", "create", "-f", "qcow2", disk_path, f"{req.disk_gb}G"], check=True)

        import libvirt
        conn = libvirt.open("qemu:///system")
        dom = conn.defineXML(xml)
        dom.create() # Starts domain
        conn.close()
        return {"message": f"VM {req.name} successfully created and started."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hypervisor/vms/{name}/action", dependencies=[Depends(get_current_user)])
def vm_action(name: str, action: str):
    if action not in ["start", "stop", "reboot", "destroy"]:
        raise HTTPException(status_code=400, detail="Invalid VM action")

    if MOCK_MODE:
        return {"message": f"Action {action} dispatched to VM {name} (MOCKED)"}

    try:
        import libvirt
        conn = libvirt.open("qemu:///system")
        dom = conn.lookupByName(name)
        if action == "start":
            dom.create()
        elif action == "stop":
            dom.shutdown()
        elif action == "reboot":
            dom.reboot(0)
        elif action == "destroy":
            # Undefine and clear files
            try:
                dom.destroy()
            except Exception:
                pass
            dom.undefine()
            disk_path = f"/var/lib/libvirt/images/{name}.qcow2"
            if os.path.exists(disk_path):
                os.remove(disk_path)
        conn.close()
        return {"message": f"Action {action} performed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Hardware & Telemetry Monitoring
@app.get("/api/system/telemetry")
def get_telemetry():
    # CPU, Memory, Disks, Network metrics
    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_count()
    mem = psutil.virtual_memory()
    
    # Storage capacities
    disk_usage = []
    for part in psutil.disk_partitions():
        if "loop" in part.device or "overlay" in part.device:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disk_usage.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            })
        except Exception:
            pass

    net_io = psutil.net_io_counters()
    
    # Read CPU Temp if available
    temp = 42.0 # default mock
    if not MOCK_MODE:
        try:
            # Parse /sys/class/thermal/thermal_zone0/temp
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = float(f.read().strip()) / 1000.0
        except Exception:
            pass

    return {
        "hostname": socket.gethostname(),
        "cpu": {
            "percent": cpu_pct,
            "cores": cpu_cores,
            "load_avg": os.getloadavg() if hasattr(os, "getloadavg") else [0.0, 0.0, 0.0]
        },
        "memory": {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent
        },
        "disks": disk_usage,
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        },
        "temperature": temp,
        "uptime": int(datetime.datetime.now().timestamp() - psutil.boot_time())
    }

# Logging & Auditing
@app.get("/api/system/logs", dependencies=[Depends(get_current_user)])
def get_logs(lines: int = 50):
    if MOCK_MODE:
        return [
            f"Jul 02 13:48:05 rocknas-host rocknas-backend[1020]: Initializing StorageManager in Mock Mode",
            f"Jul 02 13:48:10 rocknas-host smbd[1232]: Connection from 192.168.1.50 closed",
            f"Jul 02 13:49:01 rocknas-host cron[820]: (root) CMD (   [ -x /usr/lib/php/sessionclean ] && /usr/lib/php/sessionclean)",
            f"Jul 02 13:50:00 rocknas-host rocknas-backend[1020]: GET /api/system/telemetry 200 OK"
        ]

    try:
        # Call journalctl
        out = subprocess.run(["journalctl", "-n", str(lines), "--no-pager"], stdout=subprocess.PIPE, text=True)
        return out.stdout.split("\n")
    except Exception as e:
        return [f"Failed to fetch system logs: {e}"]

# Power Control & Updates
@app.post("/api/system/power", dependencies=[Depends(get_current_user)])
def system_power(action: str):
    if action not in ["reboot", "shutdown"]:
        raise HTTPException(status_code=400, detail="Action must be reboot or shutdown")
    
    if MOCK_MODE:
        return {"message": f"System action {action} triggered (MOCKED)"}

    try:
        if action == "reboot":
            subprocess.Popen(["reboot"])
        elif action == "shutdown":
            subprocess.Popen(["shutdown", "-h", "now"])
        return {"message": f"System {action} initiated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/updates", dependencies=[Depends(get_current_user)])
def check_updates():
    if MOCK_MODE:
        return {"upgradable_packages": ["linux-image-arm64", "zfsutils-linux"], "count": 2}

    try:
        subprocess.run(["apt-get", "update"], check=False)
        out = subprocess.run(["apt-get", "-s", "upgrade"], stdout=subprocess.PIPE, text=True)
        packages = []
        for line in out.stdout.split("\n"):
            if line.startswith("Inst "):
                # Inst zfsutils-linux [2.1.11-1] (2.1.12-1 Debian:trixie [arm64])
                parts = line.split()
                if len(parts) >= 2:
                    packages.append(parts[1])
        return {"upgradable_packages": packages, "count": len(packages)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/updates/upgrade", dependencies=[Depends(get_current_user)])
def apply_updates():
    if MOCK_MODE:
        return {"message": "Upgrades applied successfully (MOCKED)"}

    # Run in background
    try:
        subprocess.Popen(["apt-get", "dist-upgrade", "-y"])
        return {"message": "Dist-upgrade initiated in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bonjour (mDNS) Settings & Configuration
MDNS_CONFIG_FILE = "/etc/roqnas/mdns.json"

def load_mdns_config():
    if not os.path.exists(MDNS_CONFIG_FILE):
        try:
            os.makedirs(os.path.dirname(MDNS_CONFIG_FILE), exist_ok=True)
            config = {
                "active": True,
                "model": "TimeCapsule"
            }
            with open(MDNS_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return config
        except Exception:
            return {"active": True, "model": "TimeCapsule"}
    try:
        with open(MDNS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"active": True, "model": "TimeCapsule"}

def save_mdns_config(config):
    try:
        os.makedirs(os.path.dirname(MDNS_CONFIG_FILE), exist_ok=True)
        with open(MDNS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

def generate_avahi_services(active: bool, model: str):
    if MOCK_MODE:
        return
    
    # Paths
    smb_service = "/etc/avahi/services/smb.service"
    web_service = "/etc/avahi/services/web.service"
    device_info = "/etc/avahi/services/device-info.service"
    
    if not active:
        # Remove files if not active
        for f in [smb_service, web_service, device_info]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        # Stop Avahi
        subprocess.run(["systemctl", "stop", "avahi-daemon"], check=False)
        return

    # XML configuration contents
    smb_content = """<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_smb._tcp</type>
    <port>445</port>
  </service>
</service-group>
"""
    
    web_content = """<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h Management Portal</name>
  <service>
    <type>_http._tcp</type>
    <port>8000</port>
  </service>
</service-group>
"""
    
    device_content = f"""<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_device-info._tcp</type>
    <port>0</port>
    <txt-record>model={model}</txt-record>
  </service>
</service-group>
"""

    try:
        os.makedirs("/etc/avahi/services", exist_ok=True)
        with open(smb_service, "w") as f:
            f.write(smb_content)
        with open(web_service, "w") as f:
            f.write(web_content)
        with open(device_info, "w") as f:
            f.write(device_content)
        
        # Start/Restart Avahi
        subprocess.run(["systemctl", "enable", "avahi-daemon"], check=False)
        subprocess.run(["systemctl", "restart", "avahi-daemon"], check=False)
    except Exception as e:
        logger.error(f"Failed generating Avahi services: {e}")

@app.get("/api/system/mdns", dependencies=[Depends(get_current_user)])
def get_mdns_status():
    config = load_mdns_config()
    
    is_running = False
    if not MOCK_MODE:
        try:
            status = subprocess.run(["systemctl", "is-active", "avahi-daemon"], stdout=subprocess.PIPE, text=True)
            is_running = status.stdout.strip() == "active"
        except Exception:
            pass
    else:
        is_running = config.get("active", True)
        
    services = []
    if os.path.exists("/etc/avahi/services"):
        for f in os.listdir("/etc/avahi/services"):
            if f.endswith(".service"):
                services.append(f.replace(".service", ""))
                
    return {
        "active": is_running,
        "model": config.get("model", "TimeCapsule"),
        "services": services
    }

class MDNSConfigReq(BaseModel):
    active: bool
    model: str

@app.post("/api/system/mdns/config", dependencies=[Depends(get_current_user)])
def set_mdns_config(req: MDNSConfigReq):
    if req.model not in ["TimeCapsule", "Macmini", "MacPro", "iMac", "Xserve"]:
        raise HTTPException(status_code=400, detail="Invalid model identifier profile.")
    
    config = {
        "active": req.active,
        "model": req.model
    }
    save_mdns_config(config)
    generate_avahi_services(req.active, req.model)
    return {"message": "mDNS/Bonjour discoverability settings updated successfully."}

# RoqNAS Application Update Settings & Upgrade Manager
UPDATES_CONFIG_FILE = "/etc/roqnas/updates.json"

def load_updates_config():
    if not os.path.exists(UPDATES_CONFIG_FILE):
        try:
            os.makedirs(os.path.dirname(UPDATES_CONFIG_FILE), exist_ok=True)
            config = {
                "current_version": "v0.1.0",
                "server_url": "https://update.roqnas.org",
                "branch": "release"
            }
            with open(UPDATES_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return config
        except Exception:
            return {
                "current_version": "v0.1.0",
                "server_url": "https://update.roqnas.org",
                "branch": "release"
            }
    try:
        with open(UPDATES_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "current_version": "v0.1.0",
            "server_url": "https://update.roqnas.org",
            "branch": "release"
        }

def save_updates_config(config):
    try:
        os.makedirs(os.path.dirname(UPDATES_CONFIG_FILE), exist_ok=True)
        with open(UPDATES_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

@app.get("/api/system/app-version", dependencies=[Depends(get_current_user)])
def get_app_version():
    return load_updates_config()

@app.post("/api/system/app-version/config", dependencies=[Depends(get_current_user)])
def set_app_version_config(server_url: str, branch: str):
    if branch not in ["release", "beta", "dev"]:
        raise HTTPException(status_code=400, detail="Invalid branch name")
    config = load_updates_config()
    config["server_url"] = server_url
    config["branch"] = branch
    save_updates_config(config)
    return config

@app.post("/api/system/app-version/check", dependencies=[Depends(get_current_user)])
async def check_app_updates():
    config = load_updates_config()
    url = f"{config['server_url'].rstrip('/')}/api/version?branch={config['branch']}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                latest = data.get("version", "v0.0.5")
                has_update = latest != config["current_version"]
                return {
                    "current_version": config["current_version"],
                    "latest_version": latest,
                    "update_available": has_update,
                    "changelog": data.get("changelog", "No changelog provided."),
                    "download_url": data.get("download_url", "")
                }
    except Exception as e:
        logger.warning(f"Failed contacting update server {url}: {e}")
        
    return {
        "current_version": config["current_version"],
        "latest_version": config["current_version"],
        "update_available": False,
        "changelog": "Update server is currently unreachable or branch is up-to-date.",
        "download_url": ""
    }

@app.post("/api/system/app-version/upgrade", dependencies=[Depends(get_current_user)])
async def upgrade_app():
    config = load_updates_config()
    url = f"{config['server_url'].rstrip('/')}/api/version?branch={config['branch']}"
    download_url = ""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                download_url = data.get("download_url", "")
    except Exception:
        pass

    if not download_url:
        raise HTTPException(status_code=400, detail="No active update package url resolved from update server.")

    async def perform_upgrade():
        try:
            import httpx
            import tarfile
            dest_tar = "/tmp/roqnas_update.tar.gz"
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("GET", download_url) as response:
                    if response.status_code == 200:
                        with open(dest_tar, "wb") as f:
                            async for chunk in response.iter_bytes():
                                f.write(chunk)
            
            staging_dir = "/tmp/roqnas_staging"
            os.makedirs(staging_dir, exist_ok=True)
            with tarfile.open(dest_tar, "r:gz") as tar:
                tar.extractall(path=staging_dir)
            
            install_script = None
            for root, dirs, files in os.walk(staging_dir):
                if "install.sh" in files:
                    install_script = os.path.join(root, "install.sh")
                    break
            
            if install_script:
                subprocess.Popen(["bash", install_script])
                logger.info("Upgrade installer triggered successfully.")
        except Exception as e:
            logger.error(f"Upgrade task failed: {e}")

    asyncio.create_task(perform_upgrade())
    return {"message": "Upgrade downloading and preparing to run installer in the background."}

# ==============================================================================
# Priority 1: Advanced Networking & Link Aggregation (LAG)
# ==============================================================================

class BondConfig(BaseModel):
    name: str
    mode: str
    interfaces: List[str]
    dhcp: bool
    address: Optional[str] = ""
    gateway: Optional[str] = ""
    dns: Optional[List[str]] = []
    mtu: Optional[int] = 1500

mock_bonds = [
    {
        "name": "bond0",
        "mode": "802.3ad",
        "interfaces": ["eth0", "eth1"],
        "dhcp": True,
        "address": "192.168.1.200",
        "gateway": "192.168.1.1",
        "dns": ["1.1.1.1"],
        "mtu": 9000,
        "status": "UP"
    }
]

@app.get("/api/network/bonds", dependencies=[Depends(get_current_user)])
def list_bonds():
    global mock_bonds
    if MOCK_MODE:
        return mock_bonds

    bonds = []
    proc_bonding = "/proc/net/bonding"
    if os.path.exists(proc_bonding):
        for name in os.listdir(proc_bonding):
            interfaces = []
            mode = "unknown"
            status = "DOWN"
            try:
                with open(os.path.join(proc_bonding, name), "r") as f:
                    content = f.read()
                    mode_match = re.search(r"Bonding Mode:\s*(.+)", content)
                    if mode_match:
                        mode = mode_match.group(1).strip()
                    slaves = re.findall(r"Slave Interface:\s*(.+)", content)
                    interfaces = slaves
                    status = "UP"
            except Exception:
                pass
            
            ip = ""
            mtu = 1500
            try:
                stats = psutil.net_if_stats().get(name)
                if stats:
                    mtu = stats.mtu
                    status = "UP" if stats.isup else "DOWN"
                addrs = psutil.net_if_addrs().get(name, [])
                for addr in addrs:
                    if addr.family == 2:
                        ip = addr.address
                        break
            except Exception:
                pass

            bonds.append({
                "name": name,
                "mode": mode,
                "interfaces": interfaces,
                "dhcp": True,
                "address": ip,
                "gateway": "",
                "dns": [],
                "mtu": mtu,
                "status": status
            })
    return bonds

@app.post("/api/network/bonds", dependencies=[Depends(get_current_user)])
def create_bond(req: BondConfig):
    if not re.match(r"^bond[0-9]+$", req.name):
        raise HTTPException(status_code=400, detail="Bond name must follow /dev/bondX layout (e.g. bond0)")

    global mock_bonds
    if MOCK_MODE:
        # Update mock bonds
        mock_bonds = [b for b in mock_bonds if b["name"] != req.name]
        mock_bonds.append({
            "name": req.name,
            "mode": req.mode,
            "interfaces": req.interfaces,
            "dhcp": req.dhcp,
            "address": req.address,
            "gateway": req.gateway,
            "dns": req.dns,
            "mtu": req.mtu,
            "status": "UP"
        })
        return {"message": f"Bond {req.name} created successfully (MOCKED)"}

    # Write configs
    netdev_path = f"/etc/systemd/network/30-{req.name}.netdev"
    netdev_content = f"[NetDev]\nName={req.name}\nKind=bond\n\n[Bond]\n"
    if req.mode == "802.3ad":
        netdev_content += "Mode=802.3ad\nLACPTransmitRate=fast\nMIIMonitorSec=100ms\n"
    elif req.mode == "active-backup":
        netdev_content += "Mode=active-backup\nMIIMonitorSec=100ms\n"
    elif req.mode == "balance-alb":
        netdev_content += "Mode=balance-alb\nMIIMonitorSec=100ms\n"
    else:
        netdev_content += "Mode=balance-rr\nMIIMonitorSec=100ms\n"

    network_path = f"/etc/systemd/network/30-{req.name}.network"
    network_content = f"[Match]\nName={req.name}\n\n[Network]\n"
    if req.dhcp:
        network_content += "DHCP=yes\n"
    else:
        network_content += f"Address={req.address}\n"
        if req.gateway:
            network_content += f"Gateway={req.gateway}\n"
        for dns_ip in req.dns:
            if dns_ip:
                network_content += f"DNS={dns_ip}\n"
    network_content += f"\n[Link]\nMTUBytes={req.mtu}\n"

    try:
        with open(netdev_path, "w") as f:
            f.write(netdev_content)
        with open(network_path, "w") as f:
            f.write(network_content)

        for iface in req.interfaces:
            member_path = f"/etc/systemd/network/30-{req.name}-member-{iface}.network"
            member_content = f"[Match]\nName={iface}\n\n[Network]\nBond={req.name}\n"
            with open(member_path, "w") as f:
                f.write(member_content)

        subprocess.run(["systemctl", "restart", "systemd-networkd"], check=True)
        return {"message": f"Link Aggregation {req.name} deployed and systemd-networkd restarted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/network/bonds/{name}", dependencies=[Depends(get_current_user)])
def delete_bond(name: str):
    global mock_bonds
    if MOCK_MODE:
        mock_bonds = [b for b in mock_bonds if b["name"] != name]
        return {"message": f"Bond {name} deleted successfully (MOCKED)"}

    try:
        for f in os.listdir("/etc/systemd/network"):
            if f.startswith(f"30-{name}"):
                os.remove(os.path.join("/etc/systemd/network", f))
        subprocess.run(["systemctl", "restart", "systemd-networkd"], check=True)
        return {"message": f"Bond {name} destroyed and network settings reloaded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Priority 2: Web File Station (File Explorer)
# ==============================================================================

class ArchiveConfig(BaseModel):
    path: str
    archive_type: str
    output_name: str

class DeleteConfig(BaseModel):
    path: str

mock_files_db = {
    "/backups": [
        {"name": "backup_2026_07_01.tar.gz", "size": 45123992120, "type": "file", "mtime": "2026-07-01 12:00:00", "perms": "rw-r--r--"},
        {"name": "system_config.json", "size": 1024, "type": "file", "mtime": "2026-07-02 09:15:00", "perms": "rw-r--r--"}
    ],
    "/media": [
        {"name": "avatar_4k.mkv", "size": 8219000100, "type": "file", "mtime": "2026-06-25 22:30:12", "perms": "rwxrwxrwx"},
        {"name": "intro_music.mp3", "size": 8910020, "type": "file", "mtime": "2026-06-20 10:11:00", "perms": "rwxrwxrwx"},
        {"name": "nas_dashboard.png", "size": 2048991, "type": "file", "mtime": "2026-07-02 13:45:00", "perms": "rw-r--r--"}
    ],
    "/documents": [
        {"name": "financial_report_q2.pdf", "size": 512990, "type": "file", "mtime": "2026-06-30 17:00:00", "perms": "rw-------"},
        {"name": "todo_notes.txt", "size": 512, "type": "file", "mtime": "2026-07-02 13:50:00", "perms": "rw-r--r--"}
    ]
}

@app.get("/api/files/list", dependencies=[Depends(get_current_user)])
def list_files(path: str = "/"):
    if MOCK_MODE:
        clean_path = path.rstrip("/")
        if not clean_path:
            return [
                {"name": "backups", "size": 0, "type": "dir", "mtime": "2026-07-02 12:00:00", "perms": "rwxr-xr-x"},
                {"name": "media", "size": 0, "type": "dir", "mtime": "2026-07-02 12:00:00", "perms": "rwxr-xr-x"},
                {"name": "documents", "size": 0, "type": "dir", "mtime": "2026-07-02 12:00:00", "perms": "rwxr-xr-x"}
            ]
        if clean_path in mock_files_db:
            return mock_files_db[clean_path]
        return []

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    files = []
    try:
        import stat as stat_mod
        for entry in os.scandir(path):
            stat = entry.stat()
            perms = stat_mod.filemode(stat.st_mode)
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            files.append({
                "name": entry.name,
                "size": stat.st_size if entry.is_file() else 0,
                "type": "file" if entry.is_file() else "dir",
                "mtime": mtime,
                "perms": perms
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return files

@app.post("/api/files/create_dir", dependencies=[Depends(get_current_user)])
def create_directory(path: str, dir_name: str):
    if MOCK_MODE:
        clean_path = path.rstrip("/")
        full_path = f"{clean_path}/{dir_name}" if clean_path else f"/{dir_name}"
        if clean_path in mock_files_db:
            exists = any(f["name"] == dir_name for f in mock_files_db[clean_path])
            if not exists:
                mock_files_db[clean_path].append({
                    "name": dir_name, "size": 0, "type": "dir", "mtime": "Just now", "perms": "rwxr-xr-x"
                })
        else:
            mock_files_db[full_path] = []
        return {"message": f"Folder {dir_name} created successfully (MOCKED)"}

    full_path = os.path.join(path, dir_name)
    try:
        os.makedirs(full_path, exist_ok=True)
        return {"message": f"Folder {dir_name} created successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/delete", dependencies=[Depends(get_current_user)])
def delete_file_or_dir(req: DeleteConfig):
    import shutil
    if MOCK_MODE:
        parts = req.path.rstrip("/").split("/")
        if len(parts) >= 2:
            parent = "/" + "/".join(parts[1:-1])
            name = parts[-1]
            if parent == "/":
                parent = ""
            clean_parent = parent.rstrip("/")
            if req.path in mock_files_db:
                mock_files_db.pop(req.path)
            elif clean_parent in mock_files_db:
                mock_files_db[clean_parent] = [f for f in mock_files_db[clean_parent] if f["name"] != name]
        return {"message": f"Deleted {req.path} (MOCKED)"}

    if not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="File or folder not found")
    
    try:
        if os.path.isdir(req.path):
            shutil.rmtree(req.path)
        else:
            os.remove(req.path)
        return {"message": "Deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/archive", dependencies=[Depends(get_current_user)])
def archive_files(req: ArchiveConfig):
    import shutil
    if MOCK_MODE:
        parent = os.path.dirname(req.path)
        if parent in mock_files_db:
            mock_files_db[parent].append({
                "name": req.output_name,
                "size": 512000,
                "type": "file",
                "mtime": "Just now",
                "perms": "rw-r--r--"
            })
        return {"message": f"Archived to {req.output_name} successfully (MOCKED)"}

    try:
        output_path = os.path.join(os.path.dirname(req.path), req.output_name)
        if req.archive_type == "zip":
            shutil.make_archive(output_path.replace(".zip", ""), 'zip', req.path)
        else:
            shutil.make_archive(output_path.replace(".tar.gz", "").replace(".tgz", ""), 'gztar', req.path)
        return {"message": f"Archived to {req.output_name} successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Priority 3: VM Consoles (Serial Shell & VNC Frame Proxies)
# ==============================================================================

@app.websocket("/api/ws/vms/{name}/console")
async def vm_console_socket(websocket: WebSocket, name: str):
    await websocket.accept()
    pid = -1
    fd = -1

    if MOCK_MODE:
        pid, fd = pty.fork()
        if pid == 0:
            os.environ["TERM"] = "xterm-256color"
            os.environ["PS1"] = f"root@{name}:~# "
            os.chdir("/home/alteredgenome")
            try:
                os.execv("/bin/bash", ["/bin/bash"])
            except Exception:
                os._exit(1)
    else:
        try:
            import libvirt
            conn = libvirt.open("qemu:///system")
            dom = conn.lookupByName(name)
            xml_desc = dom.XMLDesc()
            match = re.search(r"<console\s+type=['\"]pty['\"]>\s*<source\s+path=['\"]([^'\"]+)['\"]/>", xml_desc)
            tty_path = match.group(1) if match else None
            
            if tty_path and os.path.exists(tty_path):
                fd = os.open(tty_path, os.O_RDWR | os.O_NOCTTY | os.O_NDELAY)
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NDELAY)
            else:
                pid, fd = pty.fork()
                if pid == 0:
                    try:
                        os.execv("/usr/bin/virsh", ["/usr/bin/virsh", "console", name])
                    except Exception:
                        os._exit(1)
            conn.close()
        except Exception as e:
            await websocket.send_text(f"\r\n\x1b[31m[Error opening console: {e}]\x1b[0m\r\n")
            await websocket.close()
            return

    if fd != -1:
        async def read_from_pty():
            loop = asyncio.get_running_loop()
            try:
                while True:
                    data = await loop.run_in_executor(None, os.read, fd, 1024)
                    if not data:
                        break
                    await websocket.send_text(data.decode("utf-8", errors="ignore"))
            except Exception:
                pass
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

        read_task = asyncio.create_task(read_from_pty())

        try:
            while True:
                msg = await websocket.receive_text()
                try:
                    event = json.loads(msg)
                    if event.get("type") == "resize" and pid != -1:
                        cols = event.get("cols", 80)
                        rows = event.get("rows", 24)
                        s = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(fd, termios.TIOCSWINSZ, s)
                    elif event.get("type") == "data":
                        os.write(fd, event["data"].encode("utf-8"))
                except json.JSONDecodeError:
                    os.write(fd, msg.encode("utf-8"))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            read_task.cancel()
            try:
                os.close(fd)
            except OSError:
                pass
            if pid != -1:
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass

@app.websocket("/api/ws/vms/{name}/vnc")
async def vm_vnc_proxy_socket(websocket: WebSocket, name: str):
    await websocket.accept()
    vnc_port = 5900
    if not MOCK_MODE:
        try:
            import libvirt
            conn = libvirt.open("qemu:///system")
            dom = conn.lookupByName(name)
            xml_desc = dom.XMLDesc()
            match = re.search(r"<graphics\s+type=['\"]vnc['\"]\s+port=['\"](\d+)['\"]", xml_desc)
            if match:
                vnc_port = int(match.group(1))
            conn.close()
        except Exception:
            pass

    import socket as net_socket
    try:
        loop = asyncio.get_running_loop()
        client_socket = net_socket.socket(net_socket.AF_INET, net_socket.SOCK_STREAM)
        await loop.run_in_executor(None, client_socket.connect, ("127.0.0.1", vnc_port))
    except Exception as e:
        await websocket.send_text(f"VNC Server connection failed: {e}")
        await websocket.close()
        return

    async def tcp_to_ws():
        try:
            while True:
                data = await loop.run_in_executor(None, client_socket.recv, 4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    tcp_task = asyncio.create_task(tcp_to_ws())

    try:
        while True:
            data = await websocket.receive_bytes()
            await loop.run_in_executor(None, client_socket.sendall, data)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        tcp_task.cancel()
        try:
            client_socket.close()
        except Exception:
            pass


# Web CLI Integration: WebSocket to shell
@app.websocket("/api/ws/terminal")
async def terminal_socket(websocket: WebSocket):
    await websocket.accept()
    
    # Fork a pty
    pid, fd = pty.fork()
    if pid == 0:
        # Child process: replace with login prompt for authentication
        os.environ["TERM"] = "xterm-256color"
        try:
            os.execv("/bin/login", ["/bin/login"])
        except Exception:
            os._exit(1)
    else:
        # Parent process: loop reading/writing to websocket
        logger.info(f"Pty forked with pid {pid}, fd {fd}")

        async def read_from_pty():
            loop = asyncio.get_running_loop()
            try:
                while True:
                    # Executing os.read in thread pool to avoid locking event loop
                    data = await loop.run_in_executor(None, os.read, fd, 1024)
                    if not data:
                        break
                    await websocket.send_text(data.decode("utf-8", errors="ignore"))
            except Exception:
                pass
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

        read_task = asyncio.create_task(read_from_pty())

        try:
            while True:
                msg = await websocket.receive_text()
                # Parse resize command or write standard input
                try:
                    event = json.loads(msg)
                    if event.get("type") == "resize":
                        cols = event.get("cols", 80)
                        rows = event.get("rows", 24)
                        s = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(fd, termios.TIOCSWINSZ, s)
                    elif event.get("type") == "data":
                        os.write(fd, event["data"].encode("utf-8"))
                except json.JSONDecodeError:
                    # Fallback write
                    os.write(fd, msg.encode("utf-8"))
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            read_task.cancel()
            try:
                os.close(fd)
            except OSError:
                pass
            # Kill subprocess group
            try:
                os.kill(pid, 9)
            except OSError:
                pass
            logger.info("Terminal session closed and pty destroyed.")

# Serve built frontend if dist exists
dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(dist_path):
    logger.info(f"Serving static frontend files from: {dist_path}")
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        if request.url.path.startswith("/api"):
            return exc
        return FileResponse(os.path.join(dist_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
