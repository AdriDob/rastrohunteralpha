#!/usr/bin/env python3
"""
Rastro — attack surface intelligence system.

Single-command launcher.

Usage:
    python launcher/start.py              # full stack
    python launcher/start.py --backend    # backend only
    python launcher/start.py --dashboard  # dashboard only
    python launcher/start.py --demo       # demo mode (fake dataset)
"""

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time

try:
    import psutil
except ImportError:
    psutil = None


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_PORT = 8000
DASHBOARD_PORT = 8501
TAIPY_PORT = 8502
FRONTEND_PORT = 5173
DEMO_PORT = 8001

FNULL = open(os.devnull, "w")

processes: list[subprocess.Popen] = []


def log(msg: str):
    print(f"  \033[92m•\033[0m {msg}")


def warn(msg: str):
    print(f"  \033[93m⚠\033[0m {msg}")


def err(msg: str):
    print(f"  \033[91m✗\033[0m {msg}")


def check_python():
    if sys.version_info < (3, 10):
        err("Python 3.10+ required")
        sys.exit(1)
    log(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def check_ollama():
    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            models = r.stdout.lower()
            log("Ollama detected")
            if "qwen2.5-coder" in models or "qwen2.5" in models:
                log("qwen2.5-coder model available")
            else:
                warn("qwen2.5-coder model not found — AI features disabled")
        else:
            warn("Ollama not running — AI features disabled")
    except FileNotFoundError:
        warn("Ollama not installed — AI features disabled")
    except subprocess.TimeoutExpired:
        warn("Ollama not responding — AI features disabled")


def _wait_for_health(proc: subprocess.Popen, url: str, timeout: float = 15.0) -> bool:
    """Poll URL until it returns 200 or process dies."""
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            err(f"Process exited prematurely (return code {proc.returncode})")
            try:
                _, stderr = proc.communicate(timeout=3)
                if stderr:
                    err(f"stderr:\n{stderr.decode('utf-8', errors='replace')[:2000]}")
            except Exception:
                pass
            return False
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    err(f"Health check timed out after {timeout}s — {url}")
    return False


def _wait_for_port(proc: subprocess.Popen, host: str, port: int, timeout: float = 20.0) -> bool:
    """Poll TCP port until open or process dies."""
    import socket

    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            err(f"Process exited prematurely (return code {proc.returncode})")
            try:
                _, stderr = proc.communicate(timeout=3)
                if stderr:
                    err(f"stderr:\n{stderr.decode('utf-8', errors='replace')[:2000]}")
            except Exception:
                pass
            return False
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            pass
        time.sleep(0.5)
    err(f"Port {port} not reachable after {timeout}s")
    return False


def start_backend(demo: bool = False) -> subprocess.Popen:
    port = DEMO_PORT if demo else BACKEND_PORT
    env = os.environ.copy()
    if demo:
        env["RASTRO_DEMO"] = "1"
    log(f"Starting backend on http://127.0.0.1:{port}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        stdout=FNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    if not _wait_for_health(proc, f"http://127.0.0.1:{port}/"):
        _abort("Backend failed to start")
    log("Backend ready")
    return proc


def start_dashboard(demo: bool = False) -> subprocess.Popen:
    backend_port = DEMO_PORT if demo else BACKEND_PORT
    env = os.environ.copy()
    env["RASTRO_BACKEND"] = f"http://127.0.0.1:{backend_port}"
    log(f"Starting Streamlit dashboard on http://localhost:{DASHBOARD_PORT}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
         "--server.port", str(DASHBOARD_PORT),
         "--server.headless", "true"],
        cwd=ROOT,
        stdout=FNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    if not _wait_for_port(proc, "127.0.0.1", DASHBOARD_PORT):
        _abort("Dashboard failed to start")
    log("Dashboard ready")
    return proc


def start_frontend(demo: bool = False) -> subprocess.Popen:
    log(f"Starting React frontend on http://localhost:{FRONTEND_PORT}")
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(FRONTEND_PORT)],
        cwd=os.path.join(ROOT, "frontend"),
        stdout=FNULL,
        stderr=subprocess.PIPE,
    )
    if not _wait_for_port(proc, "127.0.0.1", FRONTEND_PORT):
        _abort("React frontend failed to start")
    log("React frontend ready")
    return proc


def start_taipy_dashboard(demo: bool = False) -> subprocess.Popen:
    env = os.environ.copy()
    env["TAIPY_PORT"] = str(TAIPY_PORT)
    log(f"Starting Taipy dashboard on http://localhost:{TAIPY_PORT}")
    proc = subprocess.Popen(
        [sys.executable, "-m", "dashboard_taipy.app"],
        cwd=ROOT,
        stdout=FNULL,
        stderr=subprocess.PIPE,
        env=env,
    )
    if not _wait_for_port(proc, "127.0.0.1", TAIPY_PORT):
        _abort("Taipy dashboard failed to start")
    log("Taipy dashboard ready")
    return proc


def seed_demo_data():
    """Load fake dataset for demo mode."""
    sys.path.insert(0, ROOT)
    from database import db, models

    db.init_db()
    session = db.SessionLocal()
    try:
        existing = session.query(models.Target).first()
        if existing:
            log("Demo data already loaded")
            return

        target = models.Target(name="DemoCorp", domain="app.democorp.com")
        session.add(target)
        session.flush()

        demo_endpoints = [
            ("/api/v1/users/{uuid}", "GET", "uuid"),
            ("/api/v1/users/123/profile", "GET", "numeric_id"),
            ("/api/v1/admin/billing/export", "POST", "admin_billing"),
            ("/api/v1/org/workspace/members", "GET", "multi_tenant"),
            ("/graphql", "POST", "graphql"),
            ("/api/v1/account/transfer", "POST", "sensitive"),
            ("/api/v1/wallet/balance", "GET", "web3"),
            ("/health", "GET", "health"),
            ("/api/v1/invite/user", "POST", "identity"),
            ("/api/v1/files/upload", "POST", "upload"),
        ]
        for path, method, _ in demo_endpoints:
            ep = models.Endpoint(target_id=target.id, path=path, method=method)
            session.add(ep)

        findings_data = [
            ("IDOR en perfil de usuario", "high", "/api/v1/users/123/profile"),
            ("Exposición de billing admin", "critical", "/api/v1/admin/billing/export"),
            ("GraphQL sin rate limit", "medium", "/graphql"),
            ("Multi-tenant boundary bypass", "high", "/api/v1/org/workspace/members"),
            ("Wallet balance enumeration", "medium", "/api/v1/wallet/balance"),
        ]
        for title, severity, fpath in findings_data:
            ep = session.query(models.Endpoint).filter(
                models.Endpoint.path == fpath,
                models.Endpoint.target_id == target.id,
            ).first()
            finding = models.Finding(
                target_id=target.id,
                endpoint_id=ep.id if ep else None,
                title=title,
                severity=severity,
            )
            session.add(finding)

        session.commit()
        log(f"Loaded {len(demo_endpoints)} demo endpoints, {len(findings_data)} findings")
    finally:
        session.close()


def _abort(msg: str):
    err(msg)
    cleanup()
    sys.exit(1)


def _get_proc_info(p: subprocess.Popen) -> str:
    """Return a short label for a process based on its command line."""
    if not p.args or not isinstance(p.args, (list, tuple)):
        return f"pid={p.pid}"
    args = [str(a) for a in p.args]
    if "uvicorn" in args:
        return "backend"
    if "streamlit" in args:
        return "dashboard"
    if "dashboard_taipy" in args:
        return "taipy_dashboard"
    if "npm" in args:
        return "frontend"
    return f"pid={p.pid}"


def check_process_health() -> bool:
    """Verify all tracked child processes are alive using psutil.

    Returns True if all processes are healthy, False otherwise.
    Degrades gracefully if psutil is not available.
    """
    if psutil is None:
        return True

    all_ok = True
    for p in list(processes):
        if p.poll() is not None:
            label = _get_proc_info(p)
            err(f"{label} has exited (return code {p.returncode})")
            try:
                _, stderr = p.communicate(timeout=3)
                if stderr:
                    err(f"{label} stderr:\n{stderr.decode('utf-8', errors='replace')[:1000]}")
            except Exception:
                pass
            processes.remove(p)
            all_ok = False
            continue

        try:
            proc = psutil.Process(p.pid)
            if not proc.is_running():
                label = _get_proc_info(p)
                err(f"{label} is not running (pid={p.pid})")
                all_ok = False
            status = proc.status()
            if status == psutil.STATUS_ZOMBIE:
                label = _get_proc_info(p)
                warn(f"{label} is a zombie process (pid={p.pid})")
                all_ok = False
            children = proc.children(recursive=True)
            for child in children:
                if not child.is_running():
                    warn(f"Child process {child.pid} ({child.name()}) has crashed")
                    all_ok = False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            label = _get_proc_info(p)
            warn(f"Cannot access {label} process info (pid={p.pid})")

    return all_ok


def cleanup(signum=None, frame=None):
    print("\n  Shutting down Rastro...")
    for p in processes:
        p.terminate()
    for p in processes:
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
    FNULL.close()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    parser = argparse.ArgumentParser(description="Rastro — attack surface intelligence")
    parser.add_argument("--backend", action="store_true", help="Start backend only")
    parser.add_argument("--dashboard", nargs="?", const="streamlit", default=None,
                        choices=["streamlit", "taipy", "react"],
                        help="Start dashboard only (streamlit|taipy|react)")
    parser.add_argument("--demo", action="store_true", help="Demo mode with fake dataset")
    args = parser.parse_args()

    print()
    print("  \033[1m╔═══════════════════════════╗")
    print("  \033[1m║      R A S T R O         ║")
    print("  \033[1m║  Attack Surface Intel    ║")
    print("  \033[1m╚═══════════════════════════╝")
    print()

    check_python()
    check_ollama()

    mode = "demo" if args.demo else "production"

    if args.demo:
        log(f"Demo mode — loading fake dataset")
        seed_demo_data()

    only_backend = args.backend and not args.dashboard
    only_dashboard = bool(args.dashboard) and not args.backend
    both = not args.backend and not args.dashboard

    if both or args.backend:
        p = start_backend(demo=args.demo)
        processes.append(p)

    if both or only_dashboard:
        dash_type = args.dashboard or "streamlit"
        if dash_type == "taipy":
            p = start_taipy_dashboard(demo=args.demo)
            port = TAIPY_PORT
            port_label = "Taipy Dashboard"
        elif dash_type == "react":
            p = start_frontend(demo=args.demo)
            port = FRONTEND_PORT
            port_label = "React Frontend"
        else:
            p = start_dashboard(demo=args.demo)
            port = DASHBOARD_PORT
            port_label = "Dashboard"
        processes.append(p)

    print()
    print(f"  \033[1m{R'Urls' if mode != 'demo' else 'Demo URLs'}:\033[0m")
    if both or args.backend:
        port = DEMO_PORT if args.demo else BACKEND_PORT
        print(f"    \033[94mAPI\033[0m       http://127.0.0.1:{port}")
    if both or only_dashboard:
        dash_type = args.dashboard or "streamlit"
        if dash_type == "taipy":
            port = TAIPY_PORT
            label = "Taipy Dashboard"
        elif dash_type == "react":
            port = FRONTEND_PORT
            label = "React Frontend"
        else:
            port = DASHBOARD_PORT
            label = "Dashboard"
        print(f"    \033[94m{label}\033[0m  http://localhost:{port}")
    print()

    if both:
        log("Press Ctrl+C to stop all services")

    try:
        while True:
            for p in list(processes):
                rc = p.poll()
                if rc is not None:
                    label = _get_proc_info(p)
                    err(f"{label} stopped unexpectedly (return code {rc})")
                    processes.remove(p)

            if not processes:
                err("All processes stopped. Exiting.")
                break

            if len(processes) < 2 and both:
                warn("One service has stopped — remaining services continue")

            check_process_health()
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
