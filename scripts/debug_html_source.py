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
c.connect(env["kvm4_ip"], username=env.get("kvm4_user", "root"), password=env["kvm4_pass"], timeout=30, allow_agent=False, look_for_keys=False)

cmds = [
    "docker exec streamline-web-1 sh -c 'ls -la /app/public; wc -c /app/public/streamline.css; head -c 100 /app/public/streamline.css; echo; head -n 40 /app/app/page.js 2>/dev/null || head -n 5 /app/.next/server/app/page.js; ls /app/.next/server/app | head'",
    "curl -sSI https://download.spikeiq.cloud/ | head -20",
    "curl -sS http://127.0.0.1:3030/ | head -c 400; echo; curl -sS http://127.0.0.1:3030/streamline.css | head -c 80; echo",
    "grep -n StreamLine /etc/nginx/sites-enabled/download.spikeiq.cloud; sed -n '1,80p' /etc/nginx/sites-enabled/download.spikeiq.cloud",
]
for cmd in cmds:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:6000], flush=True)
    err = e.read().decode("utf-8", "replace")
    if err:
        print(err[:2000], flush=True)
c.close()
