# Update Server Infrastructure Setup

RoqNAS coordinates application upgrades via a decentralized update manager. Clients poll version manifests and download packaged codebase tarballs directly from an update server domain (defaulting to `https://update.roqnas.org`).

This page details how to deploy a private update server inside a Debian Linux LXC container, proxied behind **BunkerWeb** WAF / Reverse Proxy.

---

## 1. Update Server Application

The update server runs as a python FastAPI service. It parses `/etc/roqnas-update/channels.json` to map version releases to distinct download urls.

### Service Installation:
1. Create `/opt/roqnas-update/main.py`:
   ```python
   # /opt/roqnas-update/main.py
   import os, json
   from fastapi import FastAPI, Query, HTTPException
   from fastapi.staticfiles import StaticFiles
   from fastapi.responses import FileResponse

   app = FastAPI(title="RoqNAS Update Server")
   CONFIG_PATH = "/etc/roqnas-update/channels.json"
   UPDATES_DIR = "/var/www/updates"

   app.mount("/downloads", StaticFiles(directory=UPDATES_DIR), name="downloads")

   def load_channels():
       with open(CONFIG_PATH, "r") as f:
           return json.load(f)

   @app.get("/")
   def get_installer():
       deploy_script = "/opt/roqnas-update/deploy.sh"
       if os.path.exists(deploy_script):
           return FileResponse(deploy_script, media_type="text/x-shellscript")
       raise HTTPException(status_code=404, detail="Bootstrap script not found.")

   @app.get("/api/version")
   def get_version(branch: str = Query("release")):
       channels = load_channels()
       if branch not in channels:
           raise HTTPException(status_code=400, detail="Requested channel branch not found.")
       return channels[branch]

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=9000)
   ```

2. Setup virtual environment:
   ```bash
   python3 -m venv /opt/roqnas-update/venv
   /opt/roqnas-update/venv/bin/pip install fastapi uvicorn
   ```

3. Expose as a systemd daemon (`/etc/systemd/system/roqnas-update.service`):
   ```ini
   [Unit]
   Description=RoqNAS Update Server Daemon
   After=network.target

   [Service]
   WorkingDirectory=/opt/roqnas-update
   ExecStart=/opt/roqnas-update/venv/bin/python3 main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   *Enable and run: `systemctl enable --now roqnas-update.service`*

---

## 2. BunkerWeb Proxy Gateway

Deploy **BunkerWeb** WAF as the security gateway in front of your update server. BunkerWeb coordinates Let's Encrypt SSL certificates, implements Rate-Limiting to prevent denial-of-service, and blocks malicious web crawlers.

### Docker Compose Configuration Example:
```yaml
version: '3'

services:
  bunkerweb:
    image: bunkerity/bunkerweb:latest
    ports:
      - 80:8080
      - 443:8443
    volumes:
      - bw-data:/data
    environment:
      - SERVER_NAME=update.roqnas.org
      - AUTO_LETS_ENCRYPT=yes
      - USE_REVERSE_PROXY=yes
      - REVERSE_PROXY_URL=/ http://<LXC_CONTAINER_IP>:9000/
      - REVERSE_PROXY_HOST=update.roqnas.org
      - LIMIT_REQ=yes
      - LIMIT_REQ_RATE=10r/s
      - BAD_BEHAVIOR=yes
      - MAX_CLIENT_BODY_SIZE=50M

volumes:
  bw-data:
```
