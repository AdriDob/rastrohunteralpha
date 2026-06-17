"""Release Validation — smoke tests for desktop release artifacts.

Verifies:
  - Config module loads and has correct defaults
  - main_desktop entry point imports (single-process architecture)
  - serve_frontend creates an app
  - Process isolation (no subprocess/multiprocess dependencies)
  - Build scripts exist and are parseable
  - Capacitor config exists (mobile)
  - Tray controller works
  - Autostart functions exist
  - First-run onboarding
  - Port consistency (single source of truth across all components)

Usage:
    pytest tests/test_desktop_release.py -v
"""

from __future__ import annotations

import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent


# ── Bloque 5: Env config ─────────────────────────────────────────────

class TestEnvConfig:
    def test_import(self):
        from core_engines.env.config import EnvConfig, get_config
        cfg = get_config()
        assert cfg.port == 8000
        assert cfg.host == "127.0.0.1"
        assert cfg.is_production is True

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("RASTRO_PORT", "9090")
        monkeypatch.setenv("RASTRO_DESKTOP", "1")
        monkeypatch.setenv("RASTRO_DEBUG", "1")
        # Reload by re-importing (reset module state)
        import importlib
        from core_engines import env as env_module
        importlib.reload(env_module.config)
        from core_engines.env.config import get_config
        cfg = get_config()
        assert cfg.port == 9090
        assert cfg.desktop is True
        assert cfg.debug is True


# ── Bloque 1: main_desktop.py entry point ────────────────────────────

class TestMainDesktop:
    def test_import(self):
        import importlib
        mod = importlib.import_module("desktop.main_desktop")
        assert hasattr(mod, "main")
        assert hasattr(mod, "ServerThread")
        assert hasattr(mod, "_setup_logging")


# ── Bloque 4: Frontend server ─────────────────────────────────────────

class TestServeFrontend:
    def test_import(self):
        import importlib
        mod = importlib.import_module("desktop.serve_frontend")
        assert hasattr(mod, "create_app")
        assert hasattr(mod, "main")

    def test_create_app_no_dist(self):
        from desktop.serve_frontend import create_app
        app = create_app("/nonexistent")
        assert app is not None
        assert app.title == "Rastro Frontend"

    def test_create_app_with_dist(self, tmp_path):
        dist = tmp_path / "frontend" / "dist"
        dist.mkdir(parents=True)
        index = dist / "index.html"
        index.write_text("<html></html>")

        from desktop.serve_frontend import create_app
        app = create_app(str(dist))
        assert app is not None

    def test_cli_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "desktop.serve_frontend", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0


# ── Bloque 2: Build scripts ──────────────────────────────────────────

class TestBuildScripts:
    def test_build_desktop_import(self):
        import importlib
        mod = importlib.import_module("desktop.build.build_desktop")
        assert hasattr(mod, "build")

    def test_build_desktop_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "desktop.build.build_desktop", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "Build Rastro Desktop binary" in result.stdout

    def test_build_all_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "desktop.build.build_all", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0


# ── Bloque 7: Build orchestrator ─────────────────────────────────────

class TestBuildAll:
    def test_import(self):
        import importlib
        mod = importlib.import_module("desktop.build.build_all")
        assert hasattr(mod, "main")


# ── Bloque 8: Installer scripts exist ────────────────────────────────

class TestInstallerScripts:
    @pytest.mark.parametrize("script", [
        "install_linux.sh",
        "install_macos.sh",
        "install_windows.ps1",
    ])
    def test_installer_exists(self, script):
        path = PROJECT_DIR / "desktop" / "build" / script
        assert path.is_file(), f"{script} not found at {path}"

    def test_linux_installer_syntax(self):
        path = PROJECT_DIR / "desktop" / "build" / "install_linux.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"Shell check failed: {result.stderr}"

    def test_macos_installer_syntax(self):
        path = PROJECT_DIR / "desktop" / "build" / "install_macos.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"Shell check failed: {result.stderr}"

    def test_windows_installer_syntax(self):
        path = PROJECT_DIR / "desktop" / "build" / "install_windows.ps1"
        with open(path) as f:
            content = f.read()
        assert "Rastro.exe" in content
        assert "Installation complete" in content


# ── Bloque 9: First-run onboarding ──────────────────────────────────

class TestFirstRun:
    def test_settings_has_onboarding_flag(self):
        from desktop.settings import DEFAULT_SETTINGS
        assert "onboarding_complete" in DEFAULT_SETTINGS
        assert DEFAULT_SETTINGS["onboarding_complete"] is False

    def test_run_first_time(self, monkeypatch):
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        from desktop.first_run import run_first_time, is_first_run_complete

        with tempfile.TemporaryDirectory() as td:
            settings_path = os.path.join(td, "rastro", "settings.json")
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            data = dict(DEFAULT_SETTINGS)
            data["first_run"] = True
            data["first_run_complete"] = False
            with open(settings_path, "w") as f:
                json.dump(data, f)

            monkeypatch.setattr("desktop.settings._get_settings_path", lambda: settings_path)

            settings = DesktopSettings()
            result = run_first_time(settings)
            assert result is True
            assert settings.get("first_run") is False
            assert settings.get("first_run_complete") is True
            assert is_first_run_complete(settings) is True

            result = run_first_time(settings)
            assert result is False


# ── Bloque 6: Mobile build script ────────────────────────────────────

class TestMobileBuild:
    def test_build_apk_script_exists(self):
        path = PROJECT_DIR / "mobile" / "build_apk.sh"
        assert path.is_file()

    def test_build_apk_syntax(self):
        path = PROJECT_DIR / "mobile" / "build_apk.sh"
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"Shell check failed: {result.stderr}"


# ── Core / env / config ──────────────────────────────────────────────

class TestCoreEnvConfig:
    def test_module_exists(self):
        assert (PROJECT_DIR / "core_engines" / "env" / "config.py").is_file()

    def test_config_dir_default(self):
        from core_engines.env.config import EnvConfig
        cfg = EnvConfig()
        assert "rastro" in str(cfg.config_dir)

    def test_data_dir_default(self):
        from core_engines.env.config import EnvConfig
        cfg = EnvConfig()
        assert "rastro" in str(cfg.data_dir)


# ── Capacitor config exists (mobile) ─────────────────────────────────

class TestCapacitorConfig:
    def test_capacitor_config_exists(self):
        path = PROJECT_DIR / "capacitor.config.json"
        assert path.is_file(), f"capacitor.config.json not found at {path}"
        content = path.read_text()
        assert "ai.rastro.app" in content
        assert "Rastro" in content
        assert "frontend/dist" in content

    def test_capacitor_config_is_valid_json(self):
        """Validate capacitor.config.json is valid JSON with expected structure."""
        import json
        path = PROJECT_DIR / "capacitor.config.json"
        content = path.read_text()
        cfg = json.loads(content)
        assert cfg["appId"] == "ai.rastro.app"
        assert cfg["appName"] == "Rastro"
        assert cfg["webDir"] == "frontend/dist"


# ── New TrayController (Bloque 1) ────────────────────────────────────

class TestTrayController:
    def test_import(self):
        from desktop.tray import TrayController
        tc = TrayController(
            on_open_dashboard=lambda: None,
            on_open_daily_mode=lambda: None,
            on_restart=lambda: None,
            on_check_status=lambda: "Running",
            on_quit=lambda: None,
        )
        assert tc is not None
        assert tc.is_running is False

    def test_start_stop(self):
        from desktop.tray import TrayController
        tc = TrayController(
            on_open_dashboard=lambda: None,
            on_open_daily_mode=lambda: None,
            on_restart=lambda: None,
            on_check_status=lambda: "Running",
            on_quit=lambda: None,
        )
        thread = tc.start()
        if thread is not None:
            assert tc.is_running
            tc.stop()
            assert tc.is_running is False


# ── Autostart enable/disable/is_enabled (Bloque 3) ──────────────────

class TestAutostart:
    def test_enable_disable_functions_exist(self):
        from desktop.autostart import enable_autostart, disable_autostart, is_autostart_enabled
        assert callable(enable_autostart)
        assert callable(disable_autostart)
        assert callable(is_autostart_enabled)

    def test_is_enabled_returns_bool(self):
        from desktop.autostart import is_autostart_enabled
        result = is_autostart_enabled()
        assert isinstance(result, bool)


# ── Updater structure (Bloque 4) ─────────────────────────────────────

class TestUpdater:
    def test_import(self):
        import importlib
        from desktop.updater import (
            check_for_updates,
            download_update,
            verify_checksum,
            apply_update,
            rollback,
        )
        assert callable(check_for_updates)
        assert callable(download_update)
        assert callable(verify_checksum)
        assert callable(apply_update)
        assert callable(rollback)

    def test_check_updates_finds_release(self):
        from desktop.updater import check_for_updates
        result = check_for_updates("0.0.0")
        assert result is not None
        assert hasattr(result, "version")

    def test_verify_checksum_detects_mismatch(self, tmp_path):
        from desktop.updater import verify_checksum
        f = tmp_path / "test.bin"
        f.write_text("hello")
        result = verify_checksum(str(f), "0000000000000000000000000000000000000000000000000000000000000000")
        assert result is False


# ── First-run module (Bloque 6) ──────────────────────────────────────

class TestFirstRunModule:
    def test_import(self):
        from desktop.first_run import run_first_time, is_first_run_complete
        assert callable(run_first_time)
        assert callable(is_first_run_complete)


# ── Process isolation — verify no responsibility mixing ──

class TestProcessIsolation:
    def test_main_desktop_imports_no_subprocess_launcher(self):
        """main_desktop.py should not depend on old launcher or service_manager."""
        content = (PROJECT_DIR / "desktop" / "main_desktop.py").read_text()
        assert "service_manager" not in content
        assert "launcher" not in content
        assert "Popen" not in content
        assert "subprocess" not in content

    def test_tray_does_not_start_backend(self):
        """tray.py should control UI, not start backend."""
        content = (PROJECT_DIR / "desktop" / "tray.py").read_text()
        assert "ServiceManager" not in content

    def test_tray_does_not_import_main_desktop(self):
        """tray.py should not depend on main_desktop module."""
        content = (PROJECT_DIR / "desktop" / "tray.py").read_text()
        assert "main_desktop" not in content

    def test_main_desktop_uses_single_process(self):
        """main_desktop.py must not spawn child processes."""
        content = (PROJECT_DIR / "desktop" / "main_desktop.py").read_text()
        assert "subprocess" not in content
        assert "Popen" not in content
        assert "multiprocessing" not in content


# ── Port consistency — single source of truth ──────────────────────

class TestPortConsistency:
    """Validate that all components use the same backend port.

    The single source of truth is:
      core_engines.env.config.EnvConfig.port  (env var RASTRO_PORT, default 8000)
      desktop.settings.DEFAULT_SETTINGS.backend_port  (default 8000)

    Every URL builder, tray action, health check, and browser opener
    MUST use this port — never a hardcoded constant.
    """

    def test_env_config_default_port(self):
        """core_engines.env.config is the canonical port source."""
        from core_engines.env.config import EnvConfig
        cfg = EnvConfig()
        assert cfg.port == 8000, f"EnvConfig.port should be 8000, got {cfg.port}"

    def test_settings_default_port(self):
        """Desktop settings default port matches env config."""
        from desktop.settings import DEFAULT_SETTINGS
        assert DEFAULT_SETTINGS["backend_port"] == 8000, (
            f"Settings backend_port should be 8000, got {DEFAULT_SETTINGS['backend_port']}"
        )

    def test_build_dashboard_url_default_port(self):
        """build_dashboard_url default port matches canonical port."""
        from desktop.browser_opener import build_dashboard_url
        from core_engines.env.config import EnvConfig
        cfg = EnvConfig()

        url = build_dashboard_url()
        expected = f"http://127.0.0.1:{cfg.port}/"
        assert url == expected, f"Expected {expected}, got {url}"

    def test_build_dashboard_url_explicit_port(self):
        """build_dashboard_url accepts explicit port override."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000, path="/daily")
        assert url == "http://127.0.0.1:8000/daily"

    def test_build_dashboard_url_with_params(self):
        """build_dashboard_url includes query params correctly."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000, token="abc", tab="findings")
        assert "token=abc" in url
        assert "tab=findings" in url
        assert url.startswith("http://127.0.0.1:8000/")

    def test_open_dashboard_default_port(self):
        """open_dashboard default port matches canonical port."""
        from desktop.browser_opener import open_dashboard
        import inspect
        sig = inspect.signature(open_dashboard)
        default_port = sig.parameters["port"].default
        from core_engines.env.config import EnvConfig
        cfg = EnvConfig()
        assert default_port == cfg.port, (
            f"open_dashboard default port should be {cfg.port}, got {default_port}"
        )

    def test_server_thread_stores_port(self):
        """ServerThread stores the port and exposes it."""
        from desktop.main_desktop import ServerThread
        thread = ServerThread("127.0.0.1", 8000)
        assert thread.port == 8000
        assert thread.host == "127.0.0.1"

    def test_start_tray_uses_server_port(self):
        """Verify _start_tray capture uses server.port, not hardcoded constant."""
        import inspect
        from desktop.main_desktop import _start_tray
        source = inspect.getsource(_start_tray)
        # Must NOT contain port=5173
        assert "port=5173" not in source, (
            "_start_tray still has hardcoded port=5173"
        )
        # Must reference server.port or api_port
        assert "server.port" in source or "api_port" in source, (
            "_start_tray must use server.port"
        )

    def test_open_browser_uses_port_parameter(self):
        """Verify _open_browser uses its port parameter, not hardcoded constant."""
        import inspect
        from desktop.main_desktop import _open_browser
        source = inspect.getsource(_open_browser)
        # Must NOT contain port=5173
        assert "port=5173" not in source, (
            "_open_browser still has hardcoded 5173"
        )
        # first_boot branch should use 'port' variable
        assert '"port": port' in source, (
            "_open_browser must pass 'port' in ctx dict"
        )

    def test_no_hardcoded_5173_in_desktop_code(self):
        """No hardcoded 5173 remains in desktop/*.py (except docs/launcher)."""
        desktop_dir = Path(__file__).resolve().parent.parent / "desktop"
        for py_file in sorted(desktop_dir.rglob("*.py")):
            content = py_file.read_text()
            # Only search for 5173 in Python source (not strings like monetary values)
            if "5173" in content:
                rel = py_file.relative_to(desktop_dir.parent)
                pytest.fail(f"Hardcoded 5173 found in {rel}")

    def test_browser_opener_defaults_match(self):
        """build_dashboard_url and open_dashboard share the same default port."""
        from desktop.browser_opener import build_dashboard_url, open_dashboard
        import inspect
        b_sig = inspect.signature(build_dashboard_url)
        o_sig = inspect.signature(open_dashboard)
        assert b_sig.parameters["port"].default == o_sig.parameters["port"].default, (
            "build_dashboard_url and open_dashboard default ports differ"
        )


# ── Silent run — file logging ─────────────────────────────────────

class TestSilentRun:
    def test_setup_logging_creates_log_dir(self, monkeypatch, tmp_path):
        """Verify _setup_logging creates a log directory with files."""
        monkeypatch.chdir(str(tmp_path))
        from desktop.main_desktop import _setup_logging
        lifecycle_log = _setup_logging(dev=False)

        log_dir = Path(lifecycle_log).parent
        assert log_dir.is_dir()
        assert (log_dir / "rastro.log").exists()
        assert (log_dir / "lifecycle.log").exists()
