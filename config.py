import os
# Root directory that can be listed/printed. MUST be changed to your allowed folder.
BASE_DIR = os.environ.get('PRINT_BASE_DIR', r"C:\PrintRoot")
# API token for simple auth. Change this to a strong secret.
API_TOKEN = os.environ.get('PRINT_API_TOKEN', 'change_this_token')
# GhostScript executable path (console). Make sure GhostScript installed and path correct.
GS_PATH = os.environ.get('GS_PATH', 'gswin64c.exe')
# How long (seconds) to wait for a print job to appear in spooler after sending (adjust)
SPOOLER_DETECT_TIMEOUT = 10
# Poll interval for spooler checks (seconds)
SPOOLER_POLL_INTERVAL = 0.8
