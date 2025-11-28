# Remote Print Service (FastAPI)
Windows-focused remote printing service using GhostScript + Windows Spooler.

Features:
- List files under a restricted BASE_DIR
- List installed printers
- Submit print job with parameters (dpi, scale, margins, layout, duplex, copies)
- Background job processing with job status tracking
- Uses GhostScript to render/print and PyWin32 to monitor spooler

IMPORTANT:
- This service is designed to run on **Windows**.
- Install GhostScript (https://www.ghostscript.com/) and ensure `gswin64c.exe` is in PATH or set GS_PATH in config.py.
- Install Python dependencies (see requirements.txt).
- Run with: `uvicorn main:app --host 0.0.0.0 --port 8899 --workers 1`

Security:
- Configure API_TOKEN in config.py before exposing to network.
- Recommended to run behind VPN / ZeroTier / Cloudflare Tunnel or in internal network.
