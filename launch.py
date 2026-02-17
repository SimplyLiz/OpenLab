#!/usr/bin/env python3
"""Launch BioLab backend + frontend in one shot. Ctrl-C kills both."""

import os
import platform
import shutil
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")

IS_WINDOWS = platform.system() == "Windows"

# Resolve venv python — Scripts/python.exe on Windows, bin/python elsewhere
if IS_WINDOWS:
    VENV_PYTHON = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(ROOT, ".venv", "bin", "python")

BACKEND_PORT = int(os.environ.get("BIOLAB_BACKEND_PORT", "8000"))
FRONTEND_PORT = int(os.environ.get("BIOLAB_FRONTEND_PORT", "5173"))

procs: list[subprocess.Popen] = []


def kill_port(port: int) -> None:
    """Kill any process currently holding a port."""
    try:
        if IS_WINDOWS:
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
            time.sleep(0.5)
        else:
            out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
            for pid in out.splitlines():
                os.kill(int(pid), signal.SIGKILL)
            time.sleep(0.5)
    except (subprocess.CalledProcessError, ValueError, OSError):
        pass


def shutdown(*_: object) -> None:
    for p in procs:
        try:
            p.terminate()
        except OSError:
            pass
    deadline = time.time() + 3
    for p in procs:
        remaining = max(0, deadline - time.time())
        try:
            p.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Free ports
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)

    # Backend — uvicorn with app factory
    python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    print(f"\033[36m[BioLab]\033[0m Starting backend on :{BACKEND_PORT}")
    backend = subprocess.Popen(
        [
            python, "-m", "uvicorn",
            "biolab.api.app:create_app", "--factory",
            "--reload", "--port", str(BACKEND_PORT),
        ],
        cwd=ROOT,
    )
    procs.append(backend)

    # Frontend — resolve npm executable (npm.cmd on Windows)
    npm = shutil.which("npm") or ("npm.cmd" if IS_WINDOWS else "npm")
    print(f"\033[32m[BioLab]\033[0m Starting frontend on :{FRONTEND_PORT}")
    frontend = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
    )
    procs.append(frontend)

    print(f"\033[33m[BioLab]\033[0m Ctrl-C to stop both\n")

    # Wait — if either dies, kill the other
    while True:
        for p in procs:
            ret = p.poll()
            if ret is not None:
                name = "Backend" if p is backend else "Frontend"
                print(f"\033[31m[BioLab]\033[0m {name} exited with code {ret}")
                shutdown()
        time.sleep(0.5)


if __name__ == "__main__":
    main()
