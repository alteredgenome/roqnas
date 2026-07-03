from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
import os

app = FastAPI(title="RoqNAS Update Server Reference")

# Map of branches to latest versions & changelogs
RELEASES = {
    "release": {
        "version": "v0.1.0",
        "changelog": "Stable production release containing Bonjour discoverability and Apple Time Machine backup support.",
        "download_url": "https://update.roqnas.org/downloads/roqnas-release_0.1.0.tar.gz"
    },
    "beta": {
        "version": "v0.0.6-beta1",
        "changelog": "Beta build testing dynamic multi-link bonding.",
        "download_url": "https://update.roqnas.org/downloads/roqnas-beta_0.0.6.tar.gz"
    },
    "dev": {
        "version": "v0.0.7-dev",
        "changelog": "Bleeding-edge active dev commits containing mDNS time machine.",
        "download_url": "https://update.roqnas.org/downloads/roqnas-dev_latest.tar.gz"
    }
}

@app.get("/")
def get_installer():
    # Looks for deploy.sh in the local execution directory
    deploy_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.sh")
    if os.path.exists(deploy_script):
        return FileResponse(deploy_script, media_type="text/x-shellscript")
    raise HTTPException(status_code=404, detail="Bootstrap script not found.")

@app.get("/api/version")
def get_version(branch: str = Query("release")):
    # Returns the release details corresponding to requested channel branch (release, beta, dev)
    return RELEASES.get(branch, RELEASES["release"])

if __name__ == "__main__":
    import uvicorn
    # To run this server: python3 update_server_reference.py
    # Access endpoint: http://localhost:9000/api/version?branch=release
    uvicorn.run(app, host="0.0.0.0", port=9000)
