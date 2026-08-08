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

cmds = [
    "ss -tlnp | grep -E ':80|:443' || true",
    "ls -la /etc/nginx/sites-enabled/ 2>/dev/null; ls -la /etc/nginx/conf.d/ 2>/dev/null",
    "grep -Rin 'spikeiq\\|download' /etc/nginx/ 2>/dev/null | head -80 || true",
    "certbot certificates 2>/dev/null | head -100 || true",
    "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'",
]
for cmd in cmds:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace"), flush=True)
    err = e.read().decode("utf-8", "replace")
    if err:
        print(err, flush=True)
c.close()
