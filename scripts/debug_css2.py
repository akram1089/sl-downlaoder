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
    "docker exec streamline-web-1 sh -c 'find /app/.next/static -type f | head -50; echo ---; cat /app/.next/build-manifest.json; echo ---; ls -la /app/.next/static/FOZkOdMUtGDSlZOovvKNx 2>/dev/null; ls /app/.next/static/css 2>/dev/null || echo NO_CSS_DIR'",
    "docker exec streamline-web-1 sh -c 'curl -sS -o /dev/null -w \"%{http_code}\\n\" http://127.0.0.1:3000/_next/static/chunks/main-app-2ecc3bf42ae2d122.js; ls /app/app 2>/dev/null; ls /app/public'",
    "grep -n css /tmp/sl-web.log | tail -20 || true",
]
for cmd in cmds:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:8000], flush=True)
    print(e.read().decode("utf-8", "replace")[:2000], flush=True)
c.close()
