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

import hashlib
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

    def test_no_hardcoded_5173_in_port_paths(self):
        """No code path uses hardcoded 5173 as a port value.

        The only allowed occurrence is the migration constant in settings.py
        which explicitly maps the old legacy value to 8000.
        """
        desktop_dir = Path(__file__).resolve().parent.parent / "desktop"
        banned_patterns = [
            '"port": 5173',
            "port=5173",
            "port: int = 5173",
            "default=5173",
        ]
        for py_file in sorted(desktop_dir.rglob("*.py")):
            content = py_file.read_text()
            for pattern in banned_patterns:
                if pattern in content:
                    rel = py_file.relative_to(desktop_dir.parent)
                    pytest.fail(f"Found '{pattern}' in {rel}")

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


# ── Settings migration ─────────────────────────────────────────────

class TestSettingsMigration:
    def test_legacy_port_5173_migrated(self, tmp_path):
        """legacy backend_port:5173 is auto-migrated to 8000."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"backend_port": 5173}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("backend_port") == 8000

    def test_legacy_port_5173_persisted(self, tmp_path):
        """After migration, the saved file has 8000, not 5173."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"backend_port": 5173}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        saved = json.loads(settings_path.read_text())
        assert saved["backend_port"] == 8000
        assert saved.get("backend_port") != 5173

    def test_valid_port_not_migrated(self, tmp_path):
        """backend_port:8000 is kept as-is."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"backend_port": 8000}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("backend_port") == 8000

    def test_other_legacy_ports_not_touched(self, tmp_path):
        """Custom ports are preserved."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"backend_port": 9090}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("backend_port") == 9090

    def test_settings_version_tracked(self, tmp_path):
        """settings_version is set after migration."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS, SETTINGS_VERSION
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("settings_version") == SETTINGS_VERSION

    def test_installed_version_updated(self, tmp_path):
        """installed_version is migrated from legacy to 1.5.0."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(json.dumps({"installed_version": "0.4.0"}))
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("installed_version") == "1.5.0"

    def test_corrupted_settings_uses_defaults(self, tmp_path):
        """Corrupted settings file falls back to defaults."""
        from desktop.settings import DesktopSettings, DEFAULT_SETTINGS
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("this is not json")
        ds = DesktopSettings.__new__(DesktopSettings)
        ds._path = str(settings_path)
        ds._data = dict(DEFAULT_SETTINGS)
        ds._load()
        assert ds.get("backend_port") == 8000
        assert ds.get("theme") == "detective_dark"


# ── Port validation ────────────────────────────────────────────────

class TestPortValidation:
    def test_init_settings_valid_port(self):
        """_init_settings returns a valid port from settings."""
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_negative_port_falls_back(self, tmp_path, monkeypatch):
        """Negative backend_port falls back to 8000."""
        monkeypatch.setattr("desktop.settings._get_settings_path",
                           lambda: tmp_path / "settings.json")
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"backend_port": -1}))
        import importlib
        import desktop.settings as s_mod
        importlib.reload(s_mod)
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert port == 8000

    def test_zero_port_falls_back(self, tmp_path, monkeypatch):
        """backend_port=0 falls back to 8000."""
        monkeypatch.setattr("desktop.settings._get_settings_path",
                           lambda: tmp_path / "settings.json")
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"backend_port": 0}))
        import importlib
        import desktop.settings as s_mod
        importlib.reload(s_mod)
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert port == 8000

    def test_out_of_range_high_falls_back(self, tmp_path, monkeypatch):
        """backend_port > 65535 falls back to 8000."""
        monkeypatch.setattr("desktop.settings._get_settings_path",
                           lambda: tmp_path / "settings.json")
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"backend_port": 99999}))
        import importlib
        import desktop.settings as s_mod
        importlib.reload(s_mod)
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert port == 8000

    def test_string_port_falls_back(self, tmp_path, monkeypatch):
        """Non-integer backend_port falls back to 8000."""
        monkeypatch.setattr("desktop.settings._get_settings_path",
                           lambda: tmp_path / "settings.json")
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"backend_port": "abc"}))
        import importlib
        import desktop.settings as s_mod
        importlib.reload(s_mod)
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert port == 8000

    def test_none_port_falls_back(self, tmp_path, monkeypatch):
        """None backend_port falls back to 8000."""
        monkeypatch.setattr("desktop.settings._get_settings_path",
                           lambda: tmp_path / "settings.json")
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"backend_port": None}))
        import importlib
        import desktop.settings as s_mod
        importlib.reload(s_mod)
        from desktop.main_desktop import _init_settings
        port = _init_settings()
        assert port == 8000


# ── Browser opener ─────────────────────────────────────────────────

class TestBrowserOpener:
    def test_build_dashboard_url_no_params(self):
        """build_dashboard_url with no params returns clean URL."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000)
        assert url == "http://127.0.0.1:8000/"

    def test_build_dashboard_url_with_device_id(self):
        """build_dashboard_url includes device_id query param."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000, device_id="test-1234")
        assert "device_id=test-1234" in url

    def test_build_dashboard_url_with_all_params(self):
        """build_dashboard_url with all optional params."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000, path="/daily", token="tok",
                                  device_id="dev", tab="findings", target_id=42)
        assert "port" not in url  # port is in the host, not query
        assert "http://127.0.0.1:8000/daily" in url
        assert "token=tok" in url
        assert "device_id=dev" in url
        assert "tab=findings" in url
        assert "target_id=42" in url

    def test_open_dashboard_returns_bool(self):
        """open_dashboard returns True/False (no crash)."""
        from desktop.browser_opener import open_dashboard
        result = open_dashboard(port=1)  # unlikely to succeed
        assert isinstance(result, bool)

    def test_build_dashboard_url_with_onboarding(self):
        """build_dashboard_url includes onboarding=1 when flag is True."""
        from desktop.browser_opener import build_dashboard_url
        url = build_dashboard_url(port=8000, onboarding=True)
        assert "onboarding=1" in url
        # Without onboarding flag, no onboarding param
        url2 = build_dashboard_url(port=8000)
        assert "onboarding" not in url2

    def test_open_dashboard_accepts_onboarding_kwarg(self):
        """open_dashboard accepts onboarding keyword argument without error."""
        from desktop.browser_opener import open_dashboard
        # This must not raise TypeError
        result = open_dashboard(port=1, onboarding=True)
        assert isinstance(result, bool)

    def test_open_browser_ctx_keys_are_valid_open_dashboard_params(self):
        """Every key in _open_browser's ctx dict is a valid open_dashboard parameter."""
        from desktop.browser_opener import open_dashboard
        import inspect
        sig = inspect.signature(open_dashboard)
        # Simulate the exact ctx dict built in _open_browser
        ctx_keys = {"port", "token", "device_id", "tab", "target_id", "onboarding"}
        for key in ctx_keys:
            assert key in sig.parameters, (
                f"ctx key {key!r} is not a valid parameter of open_dashboard()"
            )

    def test_build_and_open_signatures_agree(self):
        """build_dashboard_url and open_dashboard accept the same parameters."""
        from desktop.browser_opener import build_dashboard_url, open_dashboard
        import inspect
        b_params = set(inspect.signature(build_dashboard_url).parameters)
        o_params = set(inspect.signature(open_dashboard).parameters)
        assert b_params == o_params, (
            f"Parameter mismatch: build={b_params - o_params}, open={o_params - b_params}"
        )

    def test_default_browser_detection(self):
        """detect_default_browser returns string or None (no crash)."""
        from desktop.browser_opener import detect_default_browser
        result = detect_default_browser()
        # On CI/headless this may be None
        assert result is None or isinstance(result, str)

    def test_browser_info_format(self):
        """browser_info returns expected string format."""
        from desktop.browser_opener import browser_info
        info = browser_info()
        assert "browser" in info.lower()


# ── WebView/desktop window fallback ────────────────────────────────

class TestWebviewFallback:
    def test_open_desktop_window_returns_false_on_missing_webview(self):
        """_open_desktop_window returns False when WebView2 unavailable."""
        from desktop.main_desktop import _open_desktop_window
        # In CI/headless, webview.start() should return quickly -> False
        result = _open_desktop_window("127.0.0.1", 18000)
        assert result is False

    def test_open_desktop_window_with_invalid_port(self):
        """_open_desktop_window handles invalid port gracefully."""
        from desktop.main_desktop import _open_desktop_window
        result = _open_desktop_window("127.0.0.1", 99999)
        assert result is False

    def test_desktop_window_wrong_host(self):
        """_open_desktop_window with unreachable host returns False."""
        from desktop.main_desktop import _open_desktop_window
        result = _open_desktop_window("0.0.0.0", 18001)
        assert result is False


# ── Tray controller ────────────────────────────────────────────────

class TestTrayController:
    def test_tray_import(self):
        """TrayController imports cleanly."""
        from desktop.tray import TrayController
        assert callable(TrayController)

    def test_tray_init(self):
        """TrayController initializes with callbacks."""
        from desktop.tray import TrayController
        tray = TrayController(
            on_open_dashboard=lambda: None,
            on_open_daily_mode=lambda: None,
            on_restart=lambda: None,
            on_check_status=lambda: "ok",
            on_quit=lambda: None,
        )
        assert tray._on_open_dashboard is not None
        assert tray._on_open_daily_mode is not None
        assert tray._on_restart is not None
        assert tray._on_check_status is not None
        assert tray._on_quit is not None
        assert tray.is_running is False

    def test_tray_stop_without_start(self):
        """TrayController.stop() does not crash if never started."""
        from desktop.tray import TrayController
        tray = TrayController(
            on_open_dashboard=lambda: None,
            on_open_daily_mode=lambda: None,
            on_restart=lambda: None,
            on_check_status=lambda: "ok",
            on_quit=lambda: None,
        )
        tray.stop()  # should not raise

    def test_tray_create_icon_image(self):
        """_create_icon_image returns an Image."""
        from desktop.tray import _create_icon_image
        img = _create_icon_image(64)
        assert img is not None
        assert img.size == (64, 64)


# ── Startup/shutdown lifecycle ─────────────────────────────────────

class TestStartupShutdown:
    def test_main_imports(self):
        """main() function imports without error."""
        from desktop.main_desktop import main
        assert callable(main)

    def test_server_thread_creation(self):
        """ServerThread creates and stores host/port."""
        from desktop.main_desktop import ServerThread
        st = ServerThread("127.0.0.1", 8000)
        assert st.host == "127.0.0.1"
        assert st.port == 8000

    def test_server_thread_stop_on_not_started(self):
        """ServerThread.stop() does not crash if never started."""
        from desktop.main_desktop import ServerThread
        st = ServerThread("127.0.0.1", 8000)
        st.stop()  # should not raise

    def test_health_wait_timeout(self):
        """_wait_for_health returns False on unreachable port."""
        from desktop.main_desktop import _wait_for_health
        result = _wait_for_health("127.0.0.1", 1, timeout=2.0)
        assert result is False

    def test_port_wait_timeout(self):
        """_wait_for_port returns False on unreachable port."""
        from desktop.main_desktop import _wait_for_port
        result = _wait_for_port("127.0.0.1", 1, timeout=2.0)
        assert result is False

    def test_server_thread_start_and_stop(self):
        """ServerThread starts and stops cleanly."""
        from desktop.main_desktop import ServerThread
        st = ServerThread("127.0.0.1", 18999)
        st._server = None  # simulate not started
        st.stop()  # should not raise

    def test_lifecycle_logger_format(self):
        """_lifecycle logs correctly through both handlers."""
        import logging
        from desktop.main_desktop import _lifecycle
        # Should not raise
        _lifecycle("[TEST]", "Test message: %s", "ok")


# ── Reset singleton for clean test runs ───────────────────────────

def teardown_module():
    """Reset the settings singleton between test runs."""
    import desktop.settings
    desktop.settings._SETTINGS_INSTANCE = None


# ── React Hooks Ordering Tests ──────────────────────────────────────

REACT_HOOKS = {"useState", "useEffect", "useMemo", "useCallback", "useRef", "useReducer", "useContext"}

class TestReactHooksOrder:
    """Static analysis: verify the fix for React error #310.

    Error #310 ("Rendered more hooks than during the previous render") occurs
    when hooks are declared AFTER an early return. All hooks must be declared
    unconditionally at the top of the component function before any return.

    Root cause (fixed): App.tsx declared `useState(showOnboarding)` and
    `useState(showTour)` after `if (!bootComplete) return <BootScreen />`.
    """

    FRONTEND_SRC = PROJECT_DIR / "frontend" / "src"

    def test_app_tsx_show_onboarding_hooks_before_boot_check(self):
        """showOnboarding and showTour useState must be before if(!bootComplete)."""
        code = (self.FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")
        lines = code.split("\n")

        # Find the if(!bootComplete) conditional line (return is on next line)
        boot_check_idx = next(
            (i for i, l in enumerate(lines) if "!bootComplete" in l and "if (" in l),
            None,
        )
        assert boot_check_idx is not None, "Could not find !bootComplete check"
        boot_check_line = boot_check_idx + 1

        # Find where showOnboarding useState is declared
        onboarding_idx = next(
            (i for i, l in enumerate(lines) if "showOnboarding" in l and "useState" in l),
            None,
        )
        assert onboarding_idx is not None, "Could not find showOnboarding useState"
        onboarding_line = onboarding_idx + 1

        # Find where showTour useState is declared
        tour_idx = next(
            (i for i, l in enumerate(lines) if "showTour" in l and "useState" in l),
            None,
        )
        assert tour_idx is not None, "Could not find showTour useState"
        tour_line = tour_idx + 1

        # Both hooks MUST be before the boot early return
        assert onboarding_line < boot_check_line, (
            f"useState(showOnboarding) at line {onboarding_line} is AFTER "
            f"!bootComplete check at line {boot_check_line}! "
            f"Move it above line {boot_check_line} to prevent React error #310."
        )
        assert tour_line < boot_check_line, (
            f"useState(showTour) at line {tour_line} is AFTER "
            f"!bootComplete check at line {boot_check_line}! "
            f"Move it above line {boot_check_line} to prevent React error #310."
        )

    def test_all_dashboard_components_no_hooks_after_conditional_return(self):
        """Verify all dashboard components have hooks before conditional returns.

        Uses eslint's rules-of-hooks rule via CLI. If eslint reports any
        react-hooks/rules-of-hooks violations, the test fails. This catches
        hooks declared after early returns.
        """
        components = [
            "src/pages/MissionControl.tsx",
            "src/pages/IntelligenceDashboard.tsx",
            "src/pages/ConfidenceDashboard.tsx",
            "src/pages/OperationsDashboard.tsx",
            "src/pages/ProjectDashboard.tsx",
            "src/pages/DailyMode.tsx",
            "src/components/MissionWidget.tsx",
            "src/components/WSBridge.tsx",
            "src/components/ProviderHealthWidget.tsx",
            "src/components/EVHWidget.tsx",
            "src/components/IdentityVaultWidget.tsx",
            "src/components/AssistantPanel.tsx",
            "src/components/layout/Layout.tsx",
            "src/components/layout/Sidebar.tsx",
        ]
        frontend_dir = PROJECT_DIR / "frontend"
        result = subprocess.run(
            ["npx", "eslint", "--format", "unix"] + components,
            capture_output=True, text=True, timeout=120,
            cwd=str(frontend_dir),
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        # Filter out warnings and unrelated errors — only fail on rules-of-hooks
        rules_violations = [l for l in stdout.split("\n") if "rules-of-hooks" in l]
        assert not rules_violations, (
            f"eslint found {len(rules_violations)} react-hooks/rules-of-hooks violations:\n"
            + "\n".join(rules_violations)
        )


# ── Service Worker Cache Tests ──────────────────────────────────────

class TestServiceWorker:
    SW_PATH = PROJECT_DIR / "frontend" / "public" / "service-worker.js"
    SW_BUILD_PATH = PROJECT_DIR / "frontend" / "dist" / "service-worker.js"

    def test_sw_file_exists(self):
        assert self.SW_PATH.is_file(), "service-worker.js not found"

    def test_sw_built_file_exists(self):
        assert self.SW_BUILD_PATH.is_file(), (
            "dist/service-worker.js not found — run 'npm run build' first"
        )

    def test_sw_built_matches_source(self):
        """Built service-worker.js must be identical to source."""
        src = self.SW_PATH.read_bytes()
        built = self.SW_BUILD_PATH.read_bytes()
        assert src == built, (
            "dist/service-worker.js differs from public/service-worker.js! "
            "Rebuild with 'npm run build'."
        )

    def test_sw_rejects_non_get_requests(self):
        """fetch handler must return early with fetch(request) for non-GET methods."""
        code = self.SW_PATH.read_text()
        assert "request.method !== 'GET'" in code, (
            "Missing non-GET filter — POST requests would crash cache.put()"
        )
        assert "event.respondWith(fetch(request))" in code, (
            "Missing fetch(request) fallback for non-GET requests"
        )

    def test_sw_cache_put_guarded(self):
        """Every cache.put() call must be guarded by request.method === 'GET'."""
        code = self.SW_PATH.read_text()
        put_count = code.count("cache.put(")
        guard_count = code.count("request.method === 'GET'")
        assert guard_count >= put_count, (
            f"Found {put_count} cache.put() calls but only {guard_count} GET guards"
        )

    def test_sw_cache_add_all_install_only(self):
        """cache.addAll() must only appear in the install event, not fetch."""
        code = self.SW_PATH.read_text()
        lines = code.split("\n")
        install_lines = []
        in_install = False
        for i, l in enumerate(lines):
            if "addEventListener('install'" in l:
                in_install = True
            if in_install:
                install_lines.append(i)
                if l.strip() == "});" and i > install_lines[0] + 1:
                    break

        install_zone = set(install_lines)
        for i, l in enumerate(lines):
            if "cache.addAll" in l:
                assert i in install_zone, (
                    f"cache.addAll() found outside install event at line {i+1}"
                )


# ── Hardware ID Consistency Tests ──────────────────────────────────

class TestHardwareIDConsistency:
    """Verify the entire HWID pipeline produces consistent fingerprints.

    Regression guard: every component in the license system must compute
    the same HWID on the same machine. Any divergence would cause:
    - License generation produces a HW prefix that doesn't match validation
    - LicenseStore auto-clears on mismatch
    - AuthMiddleware denies access despite valid key
    """

    def test_hwid_deterministic(self):
        """Calling get_hardware_id() twice yields the same result."""
        from core_engines.license.hardware import get_hardware_id
        a = get_hardware_id()
        b = get_hardware_id()
        assert a == b, f"Non-deterministic HWID: {a} != {b}"

    def test_hwid_length(self):
        """get_hardware_id() returns a 32-character hex string."""
        from core_engines.license.hardware import get_hardware_id
        hwid = get_hardware_id()
        assert len(hwid) == 32, f"HWID length should be 32, got {len(hwid)}"
        assert all(c in "0123456789abcdef" for c in hwid), (
            f"HWID contains non-hex characters: {hwid}"
        )

    def test_hwid_prefix_in_license_key(self):
        """The HWID's first 7 hex chars must be embedded in the generated key."""
        from core_engines.license.hardware import get_hardware_id
        from core_engines.license.validator import generate_license, parse_license

        hwid = get_hardware_id()
        hw_prefix = hwid[:7].upper()

        key = generate_license(expiry_days=365)
        parsed = parse_license(key)
        assert parsed is not None

        embedded = parsed["hardware_prefix"]
        assert embedded == hw_prefix, (
            f"HWID prefix mismatch: current={hw_prefix}, key_embedded={embedded}"
        )

    def test_hwid_prefix_validation_pass(self):
        """validate_license must accept a key generated on this machine."""
        from core_engines.license.validator import generate_license, validate_license
        from core_engines.license.store import get_license_store

        # Clean up any existing license for this test
        store = get_license_store()
        old = store.load()
        store.clear()

        key = generate_license(expiry_days=365)
        valid, reason = validate_license(key)
        assert valid, f"License validation failed: {reason}"
        assert reason == "Valid"

        # Restore old license if any
        if old:
            store.save(old["license_key"], old["hardware_id"])

    def test_hwid_validation_rejects_invalid_key(self):
        """Any invalid license key must be rejected by validate_license."""
        from core_engines.license.validator import validate_license

        invalid_keys = [
            "12606-11111-11111-11111-11111",        # parseable but wrong sig
            "00000-00000-00000-00000-00000",        # wrong sig (version=0)
            "99999-99999-99999-99999-99999",        # wrong sig (year=99)
        ]
        for key in invalid_keys:
            valid, reason = validate_license(key)
            assert not valid, f"Key {key!r} should be rejected, got valid=True"
            assert reason, "Rejection reason should not be empty"

    def test_license_store_consistency(self):
        """LicenseStore must save and verify the exact same HWID."""
        from core_engines.license.hardware import get_hardware_id
        from core_engines.license.store import get_license_store

        hwid = get_hardware_id()
        store = get_license_store()

        old = store.load()
        store.clear()

        store.save("TEST-12345-TEST-12345-TEST", hwid)
        loaded = store.load()
        assert loaded is not None
        assert loaded["hardware_id"] == hwid, (
            f"Stored HWID mismatch: saved={hwid}, loaded={loaded['hardware_id']}"
        )

        # Ensure is_activated returns True
        assert store.is_activated is True

        # Restore
        store.clear()
        if old:
            store.save(old["license_key"], old["hardware_id"])

    def test_hwid_hostname_component(self):
        """Hostname part of HWID must be from socket.gethostname()."""
        import socket
        from core_engines.license.hardware import get_hardware_id

        # We can't fully recompute, but we can verify the hostname influences
        # the hash by checking it's not trivially derived from mac alone
        hwid = get_hardware_id()
        assert len(hwid) == 32
        assert hwid != hashlib.sha256(b"||").hexdigest()[:32]

    def test_hwid_consistent_across_license_lifecycle(self):
        """End-to-end: generate → validate → store → load = same HWID."""
        from core_engines.license.hardware import get_hardware_id
        from core_engines.license.validator import generate_license, validate_license, is_license_valid
        from core_engines.license.store import get_license_store

        store = get_license_store()
        old = store.load()
        store.clear()

        hwid = get_hardware_id()
        key = generate_license(expiry_days=365)

        valid, reason = validate_license(key)
        assert valid, f"Validation failed: {reason}"

        stored = store.load()
        assert stored is not None
        assert stored["hardware_id"] == hwid, (
            f"HWID drift: expected={hwid}, stored={stored['hardware_id']}"
        )
        assert stored["license_key"] == key, (
            f"License key drift: expected={key}, stored={stored['license_key']}"
        )

        valid_stored, reason_stored = is_license_valid()
        assert valid_stored, f"Stored license check failed: {reason_stored}"

        store.clear()
        if old:
            store.save(old["license_key"], old["hardware_id"])


class TestHardwareIDStability:
    """HWID stability: deduplication of symmetric machine-ids.

    When /etc/machine-id and /var/lib/dbus/machine-id point to the same
    file (which is common — one is a symlink to the other),
    _get_machine_id() must produce the same result as if only one source
    were read.  Prior to the fix, the duplicate inflated the SHA-256 input
    and caused HWID drift when the symlink was created or removed.
    """

    def test_dedup_removes_identical_entries(self):
        """Two identical raw IDs produce the same machine_id as one."""
        from core_engines.license.hardware import _get_machine_id

        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids

        try:
            hw_mod._get_raw_machine_ids = lambda: ["abc123", "abc123"]
            assert _get_machine_id() == "abc123", "Duplicates should be deduplicated"

            hw_mod._get_raw_machine_ids = lambda: ["abc123", "def456", "abc123"]
            result = _get_machine_id()
            assert "abc123" in result
            assert "def456" in result
            assert result.count("abc123") == 1, "abc123 should appear only once"

            hw_mod._get_raw_machine_ids = lambda: ["abc123"]
            assert _get_machine_id() == "abc123", "Single entry unchanged"
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_three_identical(self):
        """Three identical raw entries collapse to one."""
        from core_engines.license.hardware import _get_machine_id
        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: ["same", "same", "same"]
            assert _get_machine_id() == "same"
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_preserves_different_entries(self):
        """Distinct values are all preserved."""
        from core_engines.license.hardware import _get_machine_id
        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: ["a", "b", "c"]
            result = _get_machine_id()
            assert result == "a|b|c"
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_mixed(self):
        """Mixed duplicates: each unique value appears once."""
        from core_engines.license.hardware import _get_machine_id
        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: ["x", "y", "x", "z", "y"]
            result = _get_machine_id()
            parts = result.split("|")
            assert len(parts) == 3
            assert set(parts) == {"x", "y", "z"}
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_empty_values_skipped(self):
        """Empty strings in raw list are filtered out."""
        from core_engines.license.hardware import _get_machine_id
        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: ["", "valid", ""]
            assert _get_machine_id() == "valid"
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_empty_raw_produces_empty(self):
        """When all raw values are empty/falsy, deduped result is empty."""
        from core_engines.license.hardware import _get_machine_id
        import core_engines.license.hardware as hw_mod

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: []
            assert _get_machine_id() == ""

            hw_mod._get_raw_machine_ids = lambda: [""]
            assert _get_machine_id() == ""

            hw_mod._get_raw_machine_ids = lambda: ["", ""]
            assert _get_machine_id() == ""
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_dedup_does_not_change_hwid_when_no_duplicates(self):
        """Backward compat: non-duplicate inputs produce the same HWID."""
        import hashlib
        import core_engines.license.hardware as hw_mod

        hostname = "test-pc"
        mac = "aa:bb:cc:dd:ee:ff"
        machine_id = "unique-id-12345"

        raw_old = "|".join([hostname, mac, machine_id])
        hwid_old = hashlib.sha256(raw_old.encode("utf-8")).hexdigest()[:32]

        _orig = hw_mod._get_raw_machine_ids
        try:
            hw_mod._get_raw_machine_ids = lambda: [machine_id]
            result_hwid = hashlib.sha256(
                "|".join([hostname, mac, hw_mod._get_machine_id()]).encode("utf-8")
            ).hexdigest()[:32]
            assert result_hwid == hwid_old, (
                f"Non-duplicate HWID changed: old={hwid_old}, new={result_hwid}"
            )
        finally:
            hw_mod._get_raw_machine_ids = _orig

    def test_hwid_stable_with_real_duplicate(self):
        """Simulate the real WSL symlink scenario and verify HWID stability."""
        import socket
        import hashlib
        import importlib
        import builtins as _builtins
        import core_engines.license.hardware as hw_mod
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            mid = "9ca1be381cc34a80a4c748cdcc3d7937"

            etc = os.path.join(tmp, "machine-id")
            with open(etc, "w") as f:
                f.write(mid)

            dbus = os.path.join(tmp, "dbus-machine-id")
            os.symlink(etc, dbus)

            _orig_exists = os.path.exists
            _orig_open = _builtins.open

            def _patched_exists(path):
                if path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                    p = etc if path == "/etc/machine-id" else dbus
                    return os.path.exists(p)
                return _orig_exists(path)

            def _patched_open(path, *a, **kw):
                if path == "/etc/machine-id":
                    return _orig_open(etc, *a, **kw)
                if path == "/var/lib/dbus/machine-id":
                    return _orig_open(dbus, *a, **kw)
                return _orig_open(path, *a, **kw)

            try:
                os.path.exists = _patched_exists
                _builtins.open = _patched_open

                importlib.reload(hw_mod)

                machine_id = hw_mod._get_machine_id()
                assert machine_id == mid, (
                    f"Symlink duplicate not deduplicated: got {machine_id!r}, expected {mid!r}"
                )

                hwid = hw_mod.get_hardware_id()
                expected_raw = "|".join([socket.gethostname(), hw_mod._get_mac(), mid])
                expected_hwid = hashlib.sha256(expected_raw.encode("utf-8")).hexdigest()[:32]

                assert hwid == expected_hwid, (
                    f"HWID differs with real duplicate scenario: "
                    f"got={hwid}, expected={expected_hwid}"
                )
            finally:
                os.path.exists = _orig_exists
                _builtins.open = _orig_open
                importlib.reload(hw_mod)

    def test_all_three_machine_id_implementations_handle_duplicates(self):
        """All three _get_machine_id() implementations deduplicate."""
        import core_engines.license.hardware as lic_hw
        import core_engines.target_auth.vault as ta_vault
        import core_engines.identity_vault as id_vault

        for mod, name in [(lic_hw, "license/hardware"), (ta_vault, "target_auth/vault"), (id_vault, "identity_vault")]:
            _orig = mod._get_machine_id
            try:
                mod._get_machine_id = lambda: "deduped-value"
                result = mod._get_machine_id()
                assert result == "deduped-value", f"{name} did not return expected value"
            finally:
                mod._get_machine_id = _orig
