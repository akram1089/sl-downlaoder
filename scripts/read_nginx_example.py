from pathlib import Path
import sys
import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
env = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k] = v

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    env["kvm4_ip"],
    username=env.get("kvm4_user", "root"),
    password=env["kvm4_pass"],
    timeout=30,
    allow_agent=False,
    look_for_keys=False,
)
_i, o, e = c.exec_command("cat /etc/nginx/sites-available/openreply.spikeiq.cloud")
print(o.read().decode("utf-8", "replace"))
c.close()
