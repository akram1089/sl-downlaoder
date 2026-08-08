from pathlib import Path
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env: dict[str, str] = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k] = v

host = env["kvm4_ip"]
user = env.get("kvm4_user", "root")
password = env["kvm4_pass"]
remote_env = "\n".join(f"{k}={v}" for k, v in env.items() if not k.lower().startswith("kvm4")) + "\n"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30, allow_agent=False, look_for_keys=False)


def run(cmd: str, timeout: int = 1800) -> str:
    print(">>>", cmd, flush=True)
    _stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[-12000:], flush=True)
    if err:
        print(err[-8000:], flush=True)
    if code != 0:
        raise SystemExit(f"Failed ({code}): {cmd}")
    return out


run("cd /opt/streamline && git fetch origin && git reset --hard origin/main")
sftp = client.open_sftp()
with sftp.file("/opt/streamline/.env", "w") as f:
    f.write(remote_env)
sftp.close()

run(
    "cd /opt/streamline && docker compose up -d --remove-orphans > /tmp/sl-up.log 2>&1; "
    "ec=$?; echo EXIT:$ec; cat /tmp/sl-up.log; exit $ec",
    timeout=600,
)

# nginx site + certbot
run(
    "cp /opt/streamline/deploy/nginx/download.spikeiq.cloud.conf "
    "/etc/nginx/sites-available/download.spikeiq.cloud && "
    "ln -sf /etc/nginx/sites-available/download.spikeiq.cloud /etc/nginx/sites-enabled/download.spikeiq.cloud && "
    "nginx -t && systemctl reload nginx"
)
run(
    "certbot --nginx -d download.spikeiq.cloud --non-interactive --agree-tos "
    "-m admin@spikeiq.cloud --redirect || true"
)
run("cd /opt/streamline && docker compose ps")
run(
    "sleep 3; "
    "curl -sS http://127.0.0.1:8030/api/health; echo; "
    "curl -sS -o /dev/null -w 'local_web:%{http_code}\\n' http://127.0.0.1:3030/; "
    "curl -sS -o /dev/null -w 'public_http:%{http_code}\\n' -H 'Host: download.spikeiq.cloud' http://127.0.0.1/; "
    "curl -sS -o /dev/null -w 'public_https:%{http_code}\\n' https://download.spikeiq.cloud/ || true; "
    "curl -sS https://download.spikeiq.cloud/api/health || true; echo"
)
client.close()
print("DEPLOY DONE", flush=True)
