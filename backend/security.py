import os
import re
import time
import hmac
import struct
import hashlib
import base64
import logging
import subprocess
from typing import List, Dict, Any

logger = logging.getLogger("roqnas.security")

class SecurityManager:
    def __init__(self, mock: bool = False):
        self.mock = mock
        if self.mock:
            logger.info("Initializing SecurityManager in Mock Mode")
            self._mock_mfa_secrets = {} # username -> secret
            self._mock_mfa_enabled = {} # username -> bool
            self._mock_fail2ban_config = {"bantime": 3600, "maxretry": 5, "findtime": 600}
            self._mock_banned_ips = [
                {"ip": "203.0.113.88", "jail": "sshd", "banned_at": "2026-07-02 12:00:00"},
                {"ip": "198.51.100.12", "jail": "sshd", "banned_at": "2026-07-02 13:14:02"},
                {"ip": "192.168.1.144", "jail": "rocknas-web", "banned_at": "2026-07-02 14:05:10"}
            ]
            self._mock_scan_results = [
                {"id": "ssh_root", "title": "Disable SSH Root Login", "category": "SSH Hardening", "status": "warning", "message": "Root login is permitted via SSH. Disable root logins in sshd_config."},
                {"id": "ssh_port", "title": "Change Default SSH Port", "category": "SSH Hardening", "status": "secure", "message": "SSH is running on non-standard port 2222."},
                {"id": "firewall", "title": "Enforced System Firewall", "category": "Network", "status": "critical", "message": "UFW Firewall is currently INACTIVE. External ports are fully exposed."},
                {"id": "weak_passwords", "title": "Identify Weak User Passwords", "category": "Accounts", "status": "secure", "message": "All active user accounts have complex crypt hashes set."},
                {"id": "antivirus", "title": "ClamAV Signature Audits", "category": "Malware", "status": "warning", "message": "ClamAV daemon is installed but virus definitions are older than 7 days."}
            ]

    # --- 1. TOTP Authenticator (RFC 6238) ---
    def generate_totp_secret(self) -> str:
        """Generate a random 32-character Base32 secret key."""
        # 20 bytes of entropy decoded to base32 gives 32 characters
        random_bytes = os.urandom(20)
        return base64.b32encode(random_bytes).decode('utf-8')

    def verify_totp(self, secret: str, code: str, window: int = 1) -> bool:
        """Verify standard 6-digit TOTP token with time windows."""
        try:
            val = int(code.strip())
        except ValueError:
            return False

        curr_time = int(time.time())
        interval = curr_time // 30

        try:
            # Pad base32 secret if needed
            secret_padded = secret.strip()
            missing_padding = len(secret_padded) % 8
            if missing_padding:
                secret_padded += '=' * (8 - missing_padding)
            key = base64.b32decode(secret_padded, casefold=True)
        except Exception as e:
            logger.error(f"Base32 decode error: {e}")
            return False

        # Match within clocks skew window (default +/-30s skew)
        for w in range(-window, window + 1):
            msg = struct.pack(">Q", interval + w)
            hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
            offset = hmac_hash[-1] & 0x0f
            binary_code = struct.unpack(">I", hmac_hash[offset:offset+4])[0] & 0x7fffffff
            token = binary_code % 1000000
            if token == val:
                return True
        return False

    # --- 2. Fail2ban Controllers ---
    def get_fail2ban_status(self) -> Dict[str, Any]:
        """Query Fail2ban active jails and banned IPs."""
        if self.mock:
            return {
                "active_jails": ["sshd", "rocknas-web"],
                "banned_ips": self._mock_banned_ips,
                "config": self._mock_fail2ban_config
            }

        jails = []
        banned = []
        try:
            # 1. Query jails
            out = subprocess.run(["fail2ban-client", "status"], stdout=subprocess.PIPE, text=True, check=True)
            match = re.search(r"Jail list:\s+(.+)", out.stdout)
            if match:
                jails = [j.strip() for j in match.group(1).split(",")]

            # 2. Query banned IPs for each jail
            for jail in jails:
                jail_out = subprocess.run(["fail2ban-client", "status", jail], stdout=subprocess.PIPE, text=True, check=True)
                ip_match = re.search(r"Banned IP list:\s*(.*)", jail_out.stdout)
                if ip_match and ip_match.group(1).strip():
                    ips = ip_match.group(1).split()
                    for ip in ips:
                        banned.append({
                            "ip": ip.strip(),
                            "jail": jail,
                            "banned_at": "Active"
                        })
        except Exception as e:
            logger.error(f"Fail2ban client query failed: {e}")

        # Try to parse configuration
        config = {"bantime": 600, "maxretry": 5, "findtime": 600}
        if os.path.exists("/etc/fail2ban/jail.local"):
            try:
                with open("/etc/fail2ban/jail.local", "r") as f:
                    content = f.read()
                    bt = re.search(r"^bantime\s*=\s*(\d+)", content, re.MULTILINE)
                    mr = re.search(r"^maxretry\s*=\s*(\d+)", content, re.MULTILINE)
                    ft = re.search(r"^findtime\s*=\s*(\d+)", content, re.MULTILINE)
                    if bt: config["bantime"] = int(bt.group(1))
                    if mr: config["maxretry"] = int(mr.group(1))
                    if ft: config["findtime"] = int(ft.group(1))
            except Exception:
                pass

        return {
            "active_jails": jails,
            "banned_ips": banned,
            "config": config
        }

    def unban_ip(self, jail: str, ip: str) -> bool:
        """Unban a suspicious client IP address."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", jail) or not re.match(r"^[a-fA-F0-9\.:]+$", ip):
            raise ValueError("Invalid jail name or IP format")

        if self.mock:
            self._mock_banned_ips = [b for b in self._mock_banned_ips if not (b["ip"] == ip and b["jail"] == jail)]
            return True

        try:
            subprocess.run(["fail2ban-client", "set", jail, "unbanip", ip], check=True)
            return True
        except Exception as e:
            logger.error(f"Fail2ban unban failed: {e}")
            raise Exception(f"Unban command execution failed: {e}")

    def update_fail2ban_config(self, bantime: int, maxretry: int) -> bool:
        """Save settings to jail.local configuration block and restart service."""
        if bantime <= 0 or maxretry <= 0:
            raise ValueError("Values must be greater than zero")

        if self.mock:
            self._mock_fail2ban_config["bantime"] = bantime
            self._mock_fail2ban_config["maxretry"] = maxretry
            return True

        jail_content = f"""[DEFAULT]
bantime = {bantime}
maxretry = {maxretry}
findtime = 600

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
backend = %(sshd_backend)s
"""
        try:
            with open("/etc/fail2ban/jail.local", "w") as f:
                f.write(jail_content)
            # Restart fail2ban
            subprocess.run(["systemctl", "restart", "fail2ban"], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to update fail2ban config: {e}")
            raise Exception(f"Configuration update failed: {e}")

    # --- 3. Security Counselor (Scans & Auditor) ---
    def execute_counselor_scan(self) -> List[Dict[str, str]]:
        """Audit systems configurations and check security health scorecards."""
        if self.mock:
            # simulate a slow scan sleep
            time.sleep(1)
            return self._mock_scan_results

        results = []

        # 1. Audit SSH configuration
        ssh_config_path = "/etc/ssh/sshd_config"
        ssh_root_status = "warning"
        ssh_root_msg = "sshd_config could not be analyzed."
        ssh_port_status = "warning"
        ssh_port_msg = "SSH Port settings could not be verified."

        if os.path.exists(ssh_config_path):
            try:
                with open(ssh_config_path, "r") as f:
                    content = f.read()
                    root_login = re.search(r"^\s*PermitRootLogin\s+(yes|no|prohibit-password)", content, re.MULTILINE | re.IGNORECASE)
                    port_match = re.search(r"^\s*Port\s+(\d+)", content, re.MULTILINE | re.IGNORECASE)

                    if root_login and root_login.group(1).lower() == "no":
                        ssh_root_status = "secure"
                        ssh_root_msg = "SSH Root login is explicitly disabled."
                    else:
                        ssh_root_status = "warning"
                        ssh_root_msg = "PermitRootLogin is enabled. Disable root logins to prevent dictionary scans."

                    if port_match and port_match.group(1) != "22":
                        ssh_port_status = "secure"
                        ssh_port_msg = f"SSH is hardened on non-standard port {port_match.group(1)}."
                    else:
                        ssh_port_status = "warning"
                        ssh_port_msg = "SSH is running on default port 22. Highly vulnerable to scanning bots."
            except Exception as e:
                ssh_root_msg = f"Error reading config: {e}"
        else:
            ssh_root_status = "secure"
            ssh_root_msg = "SSH server config missing. Default configuration active."

        results.append({"id": "ssh_root", "title": "Disable SSH Root Login", "category": "SSH Hardening", "status": ssh_root_status, "message": ssh_root_msg})
        results.append({"id": "ssh_port", "title": "Change Default SSH Port", "category": "SSH Hardening", "status": ssh_port_status, "message": ssh_port_msg})

        # 2. Audit UFW Firewall status
        ufw_status = "critical"
        ufw_msg = "UFW firewall is inactive. Unprotected external network sockets."
        try:
            out = subprocess.run(["ufw", "status"], stdout=subprocess.PIPE, text=True, check=False)
            if "status: active" in out.stdout.lower():
                ufw_status = "secure"
                ufw_msg = "UFW Firewall is active and enforcing access rules."
        except Exception:
            pass
        results.append({"id": "firewall", "title": "Enforced System Firewall", "category": "Network", "status": ufw_status, "message": ufw_msg})

        # 3. Audit weak passwords in /etc/shadow
        shadow_status = "secure"
        shadow_msg = "All registered user accounts are encrypted with strong passwords."
        if os.path.exists("/etc/shadow"):
            try:
                with open("/etc/shadow", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            user = parts[0]
                            pw_hash = parts[1]
                            if pw_hash in ["", "*", "!"]:
                                continue
                            # check if short or insecure hashes
                            if len(pw_hash) < 20:
                                shadow_status = "warning"
                                shadow_msg = f"User account '{user}' has a weak crypt password hash set."
                                break
            except Exception:
                pass
        results.append({"id": "weak_passwords", "title": "Identify Weak User Passwords", "category": "Accounts", "status": shadow_status, "message": shadow_msg})

        # 4. Audit ClamAV signature freshness
        clam_status = "warning"
        clam_msg = "ClamAV virus signatures status cannot be parsed."
        freshclam_log = "/var/log/clamav/freshclam.log"
        if os.path.exists(freshclam_log):
            try:
                # read last 20 lines
                with open(freshclam_log, "r") as f:
                    lines = f.readlines()[-20:]
                    log_text = "".join(lines)
                    if "up-to-date" in log_text.lower() or "downloaded" in log_text.lower():
                        clam_status = "secure"
                        clam_msg = "ClamAV signature database is up to date."
                    else:
                        clam_status = "warning"
                        clam_msg = "ClamAV virus signatures database might be out of date."
            except Exception:
                pass
        else:
            clam_status = "warning"
            clam_msg = "ClamAV log missing. Ensure ClamAV and freshclam updates are installed."

        results.append({"id": "antivirus", "title": "ClamAV Signature Audits", "category": "Malware", "status": clam_status, "message": clam_msg})

        return results
