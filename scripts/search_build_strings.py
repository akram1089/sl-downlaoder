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

# Inspect built route strings vs source files on a rebuild isn't available; search JS for unique strings
cmds = [
    "docker exec streamline-web-1 sh -c 'grep -R \"Loading StreamLine\" /app/.next -l | head; grep -R \"Paste a link\" /app/.next -l | head; grep -R \"streamline.css\" /app/.next -l | head; grep -R \"Create account\" /app/.next/server -l | head'",
    "docker exec streamline-web-1 sh -c 'grep -R \"Loading StreamLine\" /app/.next/server/app -n | head -20'",
    "docker exec streamline-web-1 sh -c 'ls -la /app/.next/server/app; ls -la /app/.next/server/app/app 2>/dev/null; strings /app/.next/server/app/page.js | grep -E \"Loading StreamLine|Paste a link|Create account|streamline.css\" | head'",
]
for cmd in cmds:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd)
    print(o.read().decode("utf-8", "replace")[:5000], flush=True)
    print(e.read().decode("utf-8", "replace")[:1000], flush=True)
c.close()
