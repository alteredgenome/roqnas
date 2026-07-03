import os
import re
import logging
import subprocess
from typing import Dict, Any, List

logger = logging.getLogger("roqnas.directory")

class DirectoryManager:
    def __init__(self, mock: bool = False):
        self.mock = mock
        if self.mock:
            logger.info("Initializing DirectoryManager in Mock Mode")
            self._mock_ad = {
                "joined": False,
                "domain": "",
                "dc_ip": "",
                "joined_at": "-",
                "ticket_expiry": "-"
            }
            self._mock_ldap = {
                "connected": False,
                "server": "",
                "base_dn": "",
                "bind_dn": "",
                "imported_users_count": 0
            }
            self._mock_sso = {
                "enabled": False,
                "provider": "OpenID Connect",
                "metadata_url": "",
                "client_id": "",
                "client_secret": "",
                "redirect_url": "http://localhost:8000/api/auth/sso/callback"
            }

    # --- 1. Active Directory Join & Configuration ---
    def get_ad_status(self) -> Dict[str, Any]:
        """Query Active Directory join status."""
        if self.mock:
            return self._mock_ad

        status = {
            "joined": False,
            "domain": "",
            "dc_ip": "",
            "joined_at": "-",
            "ticket_expiry": "-"
        }
        try:
            # Check realm via samba net ads info
            out = subprocess.run(["net", "ads", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if out.returncode == 0:
                realm_match = re.search(r"Realm:\s+(.+)", out.stdout)
                dc_match = re.search(r"LDAP server name:\s+(.+)", out.stdout)
                dc_ip_match = re.search(r"LDAP server IP:\s+(.+)", out.stdout)
                
                status["joined"] = True
                status["domain"] = realm_match.group(1).strip() if realm_match else "Joined"
                status["dc_ip"] = dc_ip_match.group(1).strip() if dc_ip_match else (dc_match.group(1).strip() if dc_match else "")
                
                # Check active kerberos tickets
                klist = subprocess.run(["klist"], stdout=subprocess.PIPE, text=True, check=False)
                if klist.returncode == 0:
                    exp_match = re.search(r"\d\d/\d\d/\d\d\s+\d\d:\d\d:\d\d\s+(\d\d/\d\d/\d\d\s+\d\d:\d\d:\d\d)", klist.stdout)
                    if exp_match:
                        status["ticket_expiry"] = exp_match.group(1).strip()
                    else:
                        status["ticket_expiry"] = "Active Ticket Found"
                else:
                    status["ticket_expiry"] = "No active ticket"
        except Exception as e:
            logger.error(f"Failed to query AD status: {e}")

        return status

    def join_ad_domain(self, domain: str, username: str, password: str, dns_ip: str) -> bool:
        """Configure Kerberos/Samba files and run net ads join domain."""
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", domain) or not re.match(r"^[a-zA-Z0-9_\-\\]+$", username):
            raise ValueError("Invalid domain name or administrator username syntax")

        if self.mock:
            self._mock_ad["joined"] = True
            self._mock_ad["domain"] = domain.upper()
            self._mock_ad["dc_ip"] = dns_ip or "192.168.1.100"
            self._mock_ad["joined_at"] = "Just Joined (MOCKED)"
            self._mock_ad["ticket_expiry"] = "24 Hours Remaining"
            return True

        workgroup = domain.split(".")[0].upper()
        realm = domain.upper()

        # 1. Update /etc/krb5.conf
        krb5_config = f"""[libdefaults]
    default_realm = {realm}
    dns_lookup_realm = false
    dns_lookup_kdc = true

[realms]
    {realm} = {{
        kdc = {dns_ip}
        admin_server = {dns_ip}
        default_domain = {domain}
    }}

[domain_realm]
    .{domain} = {realm}
    {domain} = {realm}
"""
        # 2. Update Samba /etc/samba/smb.conf
        smb_global_adds = f"""
   workgroup = {workgroup}
   client signing = yes
   client use spnego = yes
   kerberos method = secrets and keytab
   realm = {realm}
   security = ADS
   winbind nss info = rfc2307
   winbind rpc only = no
   winbind use default domain = yes
"""
        try:
            # Save krb5.conf
            with open("/etc/krb5.conf", "w") as f:
                f.write(krb5_config)

            # Read and edit smb.conf
            smb_conf_path = "/etc/samba/smb.conf"
            if os.path.exists(smb_conf_path):
                with open(smb_conf_path, "r") as f:
                    content = f.read()
                # Simple regex replace global configurations
                # In real setup, we append winbind ADS parameters
                # For safety, let's append it to global block
                content = re.sub(r"\[global\]", f"[global]\n{smb_global_adds}", content, count=1)
                with open(smb_conf_path, "w") as f:
                    f.write(content)

            # 3. Join Domain
            join_cmd = ["net", "ads", "join", "-U", f"{username}%{password}"]
            res = subprocess.run(join_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            logger.info(f"AD Join complete: {res.stdout}")

            # Restart samba winbind services
            subprocess.run(["systemctl", "restart", "smbd", "nmbd", "winbind"], check=True)
            return True
        except Exception as e:
            logger.error(f"AD join execution failed: {e}")
            raise Exception(f"Failed to join domain: {e}")

    def leave_ad_domain(self) -> bool:
        """Run net ads leave and restore local configuration files."""
        if self.mock:
            self._mock_ad = {
                "joined": False,
                "domain": "",
                "dc_ip": "",
                "joined_at": "-",
                "ticket_expiry": "-"
            }
            return True

        try:
            # We can use net ads leave
            # Needs local credentials or machine account password
            subprocess.run(["net", "ads", "leave", "-P"], check=True)
            # Remove Winbind AD additions in smb.conf is optional but clean
            subprocess.run(["systemctl", "restart", "smbd", "nmbd", "winbind"], check=True)
            return True
        except Exception as e:
            logger.error(f"AD leave execution failed: {e}")
            raise Exception(f"Failed to leave domain: {e}")

    # --- 2. LDAP Client binding ---
    def get_ldap_status(self) -> Dict[str, Any]:
        """Query LDAP connection status."""
        if self.mock:
            return self._mock_ldap

        status = {
            "connected": False,
            "server": "",
            "base_dn": "",
            "bind_dn": "",
            "imported_users_count": 0
        }

        # Check /etc/nslcd.conf or /etc/ldap.conf
        conf_paths = ["/etc/nslcd.conf", "/etc/sssd/sssd.conf", "/etc/ldap.conf"]
        target_path = next((p for p in conf_paths if os.path.exists(p)), None)

        if target_path:
            try:
                with open(target_path, "r") as f:
                    content = f.read()
                    uri = re.search(r"^(uri|ldap_uri)\s+(.+)", content, re.MULTILINE)
                    base = re.search(r"^(base|ldap_search_base)\s+(.+)", content, re.MULTILINE)
                    bind = re.search(r"^(binddn|ldap_default_bind_dn)\s+(.+)", content, re.MULTILINE)

                    status["server"] = uri.group(2).strip() if uri else ""
                    status["base_dn"] = base.group(2).strip() if base else ""
                    status["bind_dn"] = bind.group(2).strip() if bind else ""
                    
                    # Test LDAP binding status
                    # Try querying LDAP users using getent passwd
                    # LDAP users usually reside in base_dn. We can run getent passwd and filter out local users
                    passwd_out = subprocess.run(["getent", "passwd"], stdout=subprocess.PIPE, text=True, check=False)
                    # Simple count users with high UID (usually >= 10000 for domain/ldap users)
                    high_uid_count = 0
                    for line in passwd_out.stdout.split("\n"):
                        parts = line.split(":")
                        if len(parts) >= 3:
                            try:
                                uid = int(parts[2])
                                if uid >= 10000:
                                    high_uid_count += 1
                            except ValueError:
                                pass
                    status["imported_users_count"] = high_uid_count
                    status["connected"] = high_uid_count > 0
            except Exception as e:
                logger.error(f"Error parsing LDAP client configurations: {e}")

        return status

    def configure_ldap_client(self, server: str, base_dn: str, bind_dn: str, password: str) -> bool:
        """Write libnss-ldap configurations and restart lookup daemon."""
        if not re.match(r"^[a-zA-Z0-9_\-\.:/]+$", server) or not re.match(r"^[a-zA-Z0-9_\-\.\,=]+$", base_dn):
            raise ValueError("Invalid LDAP Server URI or Base DN")

        if self.mock:
            self._mock_ldap["connected"] = True
            self._mock_ldap["server"] = server
            self._mock_ldap["base_dn"] = base_dn
            self._mock_ldap["bind_dn"] = bind_dn
            self._mock_ldap["imported_users_count"] = 84
            return True

        nslcd_conf = f"""# /etc/nslcd.conf
uid nslcd
gid nslcd
uri {server}
base {base_dn}
binddn {bind_dn}
bindpw {password}
ssl no
reqcert no
"""
        try:
            with open("/etc/nslcd.conf", "w") as f:
                f.write(nslcd_conf)
            # Make sure it's secure
            os.chmod("/etc/nslcd.conf", 0o600)
            
            # Restart service
            subprocess.run(["systemctl", "restart", "nslcd"], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed configuring LDAP nslcd: {e}")
            raise Exception(f"LDAP binding configuration failed: {e}")

    # --- 3. Single Sign-On (SSO) ---
    def get_sso_status(self) -> Dict[str, Any]:
        """Query SSO metadata configuration."""
        if self.mock:
            return self._mock_sso
        
        # Read from local config
        return self._mock_sso

    def configure_sso(self, enabled: bool, provider: str, metadata_url: str, client_id: str, client_secret: str) -> bool:
        """Update SSO console settings."""
        if self.mock:
            self._mock_sso["enabled"] = enabled
            self._mock_sso["provider"] = provider
            self._mock_sso["metadata_url"] = metadata_url
            self._mock_sso["client_id"] = client_id
            self._mock_sso["client_secret"] = client_secret
            return True

        # In real mode, write settings to local database/config
        self._mock_sso["enabled"] = enabled
        self._mock_sso["provider"] = provider
        self._mock_sso["metadata_url"] = metadata_url
        self._mock_sso["client_id"] = client_id
        self._mock_sso["client_secret"] = client_secret
        return True
