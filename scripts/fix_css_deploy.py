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

remote_env = "\n".join(f"{k}={v}" for k, v in env.items() if not k.lower().startswith("kvm4")) + "\n"

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


def run(cmd: str, timeout: int = 900) -> None:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    code = o.channel.recv_exit_status()
    if out:
        print(out[-9000:], flush=True)
    if err:
        print(err[-3000:], flush=True)
    if code != 0:
        raise SystemExit(f"Failed ({code}): {cmd}")


run("cd /opt/streamline && git fetch origin && git reset --hard origin/main")
sftp = c.open_sftp()
with sftp.file("/opt/streamline/.env", "w") as f:
    f.write(remote_env)
sftp.close()
run(
    "cd /opt/streamline && DOCKER_BUILDKIT=1 docker compose build web > /tmp/sl-web.log 2>&1; "
    "ec=$?; echo EXIT:$ec; tail -n 60 /tmp/sl-web.log; exit $ec"
)
run("cd /opt/streamline && docker compose up -d web")
run(
    "cp /opt/streamline/deploy/nginx/download.spikeiq.cloud.conf "
    "/etc/nginx/sites-available/download.spikeiq.cloud && "
    "ln -sf /etc/nginx/sites-available/download.spikeiq.cloud /etc/nginx/sites-enabled/download.spikeiq.cloud && "
    "nginx -t && systemctl reload nginx"
)
run(
    "sleep 2; "
    "curl -sS https://download.spikeiq.cloud/ | head -c 500; echo; "
    "curl -sS https://download.spikeiq.cloud/ | grep -o 'streamline.css' | head; "
    "curl -sS -o /dev/null -w 'css:%{http_code}\\n' https://download.spikeiq.cloud/streamline.css; "
    "curl -sS https://download.spikeiq.cloud/ | grep -o 'Paste a link\\|Loading StreamLine\\|Create account' | head -5"
)
c.close()
print("DONE", flush=True)
