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
    "docker exec streamline-web-1 sh -c 'ls -la /app; ls -la /app/.next 2>/dev/null; ls -la /app/.next/static 2>/dev/null | head; find /app -name \"*.css\" 2>/dev/null | head -20'",
    "curl -sS -D- -o /dev/null http://127.0.0.1:3030/app | head -30",
    "curl -sS http://127.0.0.1:3030/app | head -c 2000",
    "curl -sS -o /dev/null -w '%{http_code} %{content_type}\\n' http://127.0.0.1:3030/_next/static/css/ 2>/dev/null || true",
    "docker logs --tail 40 streamline-web-1",
]
for cmd in cmds:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace"), flush=True)
    err = e.read().decode("utf-8", "replace")
    if err:
        print(err, flush=True)
c.close()
