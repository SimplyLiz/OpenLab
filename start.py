"""BioLab bootstrap script — setup, serve, and manage all components.

Usage:
    python start.py setup      — Initialize DB, fetch genome, import
    python start.py server     — Start FastAPI (uvicorn)
    python start.py dashboard  — Start Streamlit dashboard
    python start.py dagster    — Start Dagster webserver
    python start.py all        — Start server + dashboard + dagster
    python start.py status     — Health check all services
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure biolab is importable
sys.path.insert(0, str(Path(__file__).parent / "src"))


def cmd_setup():
    """Initialize database, fetch genome, and import."""
    print("=== BioLab Setup ===\n")

    # 1. Initialize database
    print("[1/3] Initializing database...")
    from biolab.db.models.base import Base
    from biolab.db import get_engine
    Base.metadata.create_all(get_engine())
    print("  Database tables created.\n")

    # 2. Check for genome data
    print("[2/3] Checking genome data...")
    from biolab.db import get_session_factory
    from biolab.db.models.gene import Gene
    factory = get_session_factory()
    with factory() as db:
        gene_count = db.query(Gene).count()

    if gene_count > 0:
        print(f"  Found {gene_count} genes in database.\n")
    else:
        print("  No genes found. Import a genome:")
        print("    biolab init                    (fetch JCVI-syn3A from NCBI)")
        print("    biolab genes import file.gb    (import GenBank file)\n")

    # 3. Check configuration
    print("[3/3] Configuration check...")
    from biolab.config import config
    checks = {
        "Database": config.database.url,
        "LLM Provider": config.llm.provider,
        "LLM API Key": "set" if (config.llm.anthropic_api_key or config.llm.openai_api_key) else "NOT SET",
        "NCBI API Key": "set" if config.ncbi.api_key else "optional",
        "HF Token": "set" if config.tools.hf_token else "optional (for ESMFold)",
        "Structure Dir": config.tools.structure_dir,
    }
    for name, value in checks.items():
        status = "OK" if value and value != "NOT SET" else "WARNING"
        marker = "+" if status == "OK" else "!"
        print(f"  [{marker}] {name}: {value}")

    print("\n=== Setup complete ===")


def cmd_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the FastAPI server."""
    print(f"Starting BioLab API server on {host}:{port}...")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "biolab.api.app:create_app",
        "--factory",
        "--host", host,
        "--port", str(port),
        "--reload",
    ])


def cmd_dashboard(port: int = 8501):
    """Start the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    print(f"Starting BioLab dashboard on port {port}...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", str(port),
        "--server.headless", "true",
    ])


def cmd_dagster(port: int = 3000):
    """Start the Dagster webserver."""
    print(f"Starting Dagster webserver on port {port}...")
    subprocess.run([
        sys.executable, "-m", "dagster", "dev",
        "-p", str(port),
    ])


def cmd_all():
    """Start all services as subprocesses."""
    print("Starting all BioLab services...\n")

    processes = []

    # API server
    proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "biolab.api.app:create_app",
        "--factory",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])
    processes.append(("API Server (8000)", proc))
    print("  Started API server on :8000")

    # Dashboard
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    proc = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", "8501",
        "--server.headless", "true",
    ])
    processes.append(("Dashboard (8501)", proc))
    print("  Started dashboard on :8501")

    # Dagster (optional)
    try:
        import dagster
        proc = subprocess.Popen([
            sys.executable, "-m", "dagster", "dev",
            "-p", "3000",
        ])
        processes.append(("Dagster (3000)", proc))
        print("  Started Dagster on :3000")
    except ImportError:
        print("  Dagster not installed, skipping (pip install dagster dagster-webserver)")

    print(f"\nAll services running. Press Ctrl+C to stop.\n")

    try:
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"  WARNING: {name} exited with code {proc.returncode}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for name, proc in processes:
            proc.terminate()
        for name, proc in processes:
            proc.wait(timeout=10)
        print("All services stopped.")


def cmd_status():
    """Check health of all services."""
    import httpx

    services = [
        ("API Server", "http://localhost:8000/health"),
        ("Dashboard", "http://localhost:8501/_stcore/health"),
        ("Dagster", "http://localhost:3000/server_info"),
    ]

    print("=== BioLab Service Status ===\n")

    for name, url in services:
        try:
            resp = httpx.get(url, timeout=3.0)
            if resp.status_code == 200:
                print(f"  [+] {name}: running ({url})")
            else:
                print(f"  [!] {name}: HTTP {resp.status_code}")
        except Exception:
            print(f"  [-] {name}: not running")

    # Database check
    try:
        from biolab.db import get_session_factory
        from biolab.db.models.gene import Gene
        factory = get_session_factory()
        with factory() as db:
            count = db.query(Gene).count()
        print(f"  [+] Database: {count} genes")
    except Exception as e:
        print(f"  [-] Database: error ({e})")

    print()


COMMANDS = {
    "setup": cmd_setup,
    "server": cmd_server,
    "dashboard": cmd_dashboard,
    "dagster": cmd_dagster,
    "all": cmd_all,
    "status": cmd_status,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Available commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
