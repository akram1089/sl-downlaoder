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


def run(cmd: str, timeout: int = 900) -> None:
    print(">>>", cmd, flush=True)
    _i, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", "replace")
    err = e.read().decode("utf-8", "replace")
    code = o.channel.recv_exit_status()
    if out:
        print(out[-8000:], flush=True)
    if err:
        print(err[-4000:], flush=True)
    if code != 0:
        raise SystemExit(f"Failed ({code}): {cmd}")


run("cd /opt/streamline && git fetch origin && git reset --hard origin/main")
run(
    "cd /opt/streamline && DOCKER_BUILDKIT=1 docker compose build web > /tmp/sl-web.log 2>&1; "
    "ec=$?; echo EXIT:$ec; tail -n 50 /tmp/sl-web.log; exit $ec"
)
run("cd /opt/streamline && docker compose up -d web")
c.close()
print("WEB UPDATED", flush=True)
