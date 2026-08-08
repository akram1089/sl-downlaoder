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

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    env["kvm4_ip"],
    username=env.get("kvm4_user", "root"),
    password=env["kvm4_pass"],
    timeout=30,
    allow_agent=False,
    look_for_keys=False,
)


def run(cmd: str, timeout: int = 1800) -> str:
    print(">>>", cmd, flush=True)
    _i, o, e = client.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    code = o.channel.recv_exit_status()
    if out:
        print(out[-14000:], flush=True)
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
    "cd /opt/streamline && DOCKER_BUILDKIT=1 docker compose build --no-cache api worker web "
    "> /tmp/sl-build.log 2>&1; ec=$?; echo EXIT:$ec; tail -n 80 /tmp/sl-build.log; exit $ec",
    timeout=1800,
)
run(
    "cd /opt/streamline && docker compose up -d --remove-orphans > /tmp/sl-up.log 2>&1; "
    "ec=$?; echo EXIT:$ec; cat /tmp/sl-up.log; exit $ec"
)
run(
    "docker exec streamline-api-1 sh -c 'deno --version; python -c \"import yt_dlp; print(yt_dlp.version.__version__)\"'"
)
run("curl -sS https://download.spikeiq.cloud/api/health; echo")
client.close()
print("REBUILD DONE", flush=True)
