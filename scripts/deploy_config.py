# Deploy helper — do not commit secrets; reads local .env
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
vals = dotenv_values(ROOT / ".env")
for k, v in vals.items():
    if v is not None:
        os.environ.setdefault(k, v)

HOST = os.environ.get("kvm4_ip")
USER = os.environ.get("kvm4_user", "root")
PASSWORD = os.environ.get("kvm4_pass")
REPO = "https://github.com/akram1089/sl-downlaoder.git"
REMOTE_DIR = "/opt/streamline"

if not HOST or not PASSWORD:
    print("Missing kvm4_ip / kvm4_pass in .env", file=sys.stderr)
    sys.exit(1)
