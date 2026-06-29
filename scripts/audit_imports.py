#!/usr/bin/env python3
"""ORION Runtime Import Audit — detects forbidden dependencies in UI mode.

Scans all Python files in the project for:
  - WSL/Linux-specific paths (/mnt/, /proc/version)
  - win32service* imports (only allowed in desktop.service)
  - desktop.service import (only allowed in run.py --service mode)
  - Direct subprocess.Popen usage (only for build mode)
  - Hardcoded development paths

Usage:
    python scripts/audit_imports.py                          # Scan all source
    python scripts/audit_imports.py --json                   # JSON output
    python scripts/audit_imports.py --ci                     # CI mode
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

INCLUDE_DIRS = [
    "api",
    "core_engines",
    "database",
    "desktop",
    "core",
]

EXCLUDE_DIRS = [
    "__pycache__",
    ".venv",
    "node_modules",
    "archive_cleanup",
    "build",
    "dist",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".roo",
]

EXCLUDE_FILES = [
    "audit_imports.py",
    "build_release.py",
    "build_windows_exe.py",
    "smoke_test.py",
    "test_portable.py",
    "test_installer.py",
    "validate_assets.py",
]

# Prohibited patterns in UI mode
PROHIBITED_PATTERNS: list[dict] = [
    {
        "id": "WSL-PATH",
        "pattern": "/mnt/",
        "severity": "BLOCKER",
        "message": "WSL path detected — release code must not reference /mnt/",
        "allowed_in": [],
    },
    {
        "id": "WSL-PROC-VERSION",
        "pattern": "/proc/version",
        "severity": "BLOCKER",
        "message": "/proc/version access detected — WSL dependency",
        "allowed_in": ["desktop/boot_guard.py", "core/utils/paths.py"],
    },
    {
        "id": "PYWIN32-SERVICE",
        "pattern": "win32service",
        "severity": "HIGH",
        "message": "win32service* import detected outside desktop/service.py",
        "allowed_in": ["desktop/service.py", "desktop/service_util.py", "desktop/boot_guard.py"],
    },
    {
        "id": "DESKTOP-SERVICE-IMPORT",
        "pattern": "from desktop.service import",
        "severity": "HIGH",
        "message": "desktop.service imported outside run.py or desktop/service_util.py",
        "allowed_in": ["desktop/service_util.py", "run.py"],
    },
    {
        "id": "SUBPROCESS-POPEN",
        "pattern": "Popen",
        "severity": "MEDIUM",
        "message": "subprocess.Popen detected — should only be in build/test scripts",
        "allowed_in": ["scripts/", "run.py", "desktop/updater.py"],
    },
]

FORBIDDEN_IMPORTS: dict[str, list[str]] = {
    "desktop/service.py": {
        "allowed_importers": [
            "run.py",
            "desktop/service_util.py",
        ],
    },
}


def should_scan(path: Path) -> bool:
    rel = path.relative_to(PROJECT_ROOT)
    parts = rel.parts

    # Check exclusion dirs
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return False

    # Only scan Python files
    if path.suffix != ".py":
        return False

    # Check inclusion dirs
    if len(parts) >= 2 and parts[0] in INCLUDE_DIRS:
        return True
    if len(parts) == 1 and parts[0] in [f for f in EXCLUDE_FILES] + ["run.py"]:
        return True
    if len(parts) >= 1 and parts[-1] == "run.py":
        return True

    return False


def check_pattern(content: str, filepath: Path) -> list[dict]:
    findings: list[dict] = []
    lines = content.split("\n")
    rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace("\\", "/")

    for rule in PROHIBITED_PATTERNS:
        allowed = rule["allowed_in"]
        if any(rel_path == a or rel_path.startswith(a.rstrip("/")) for a in allowed):
            continue

        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            if rule["pattern"] in line:
                findings.append({
                    "file": rel_path,
                    "line": i,
                    "severity": rule["severity"],
                    "id": rule["id"],
                    "message": rule["message"],
                    "code": stripped[:120],
                })
    return findings


def check_imports(content: str, filepath: Path) -> list[dict]:
    """AST-based import checking for cross-module dependencies."""
    findings: list[dict] = []
    rel_path = str(filepath.relative_to(PROJECT_ROOT)).replace("\\", "/")

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [{
            "file": rel_path,
            "line": 0,
            "severity": "WARN",
            "id": "SYNTAX-ERROR",
            "message": "File could not be parsed",
            "code": "",
        }]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_import_name(alias.name, rel_path, node.lineno, findings)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _check_import_name(node.module, rel_path, node.lineno, findings)

    return findings


def _check_import_name(name: str, rel_path: str, lineno: int, findings: list[dict]) -> None:
    # Check for win32service in non-service files
    if "win32service" in name and rel_path not in [
        "desktop/service.py",
        "desktop/service_util.py",
    ]:
        findings.append({
            "file": rel_path,
            "line": lineno,
            "severity": "HIGH",
            "id": "PYWIN32-IMPORT",
            "message": f"win32* import ({name}) in non-service file",
            "code": f"import {name}",
        })

    # Check for desktop.service in non-allowed files
    if name == "desktop.service" or name.startswith("desktop.service."):
        if rel_path not in ["run.py", "desktop/service_util.py"]:
            findings.append({
                "file": rel_path,
                "line": lineno,
                "severity": "HIGH",
                "id": "SERVICE-IMPORT",
                "message": "desktop.service imported outside allowed files",
                "code": f"import {name}",
            })


def scan_file(path: Path) -> list[dict]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{
            "file": str(path),
            "line": 0,
            "severity": "ERROR",
            "id": "READ-ERROR",
            "message": f"Cannot read file: {e}",
            "code": "",
        }]

    findings = []
    findings.extend(check_pattern(content, path))
    findings.extend(check_imports(content, path))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION Import Audit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--ci", action="store_true", help="CI mode (exit code)")
    parser.add_argument("--fix", action="store_true", help="Fix mode (not implemented)")
    args = parser.parse_args()

    all_findings: list[dict] = []
    files_scanned = 0

    for include_dir in INCLUDE_DIRS:
        dir_path = PROJECT_ROOT / include_dir
        if dir_path.is_dir():
            for f in sorted(dir_path.rglob("*.py")):
                if should_scan(f):
                    files_scanned += 1
                    all_findings.extend(scan_file(f))

    # Also scan root-level files
    for f in sorted(PROJECT_ROOT.glob("*.py")):
        if should_scan(f):
            files_scanned += 1
            all_findings.extend(scan_file(f))

    # Sort by severity
    severity_order = {"BLOCKER": 0, "HIGH": 1, "MEDIUM": 2, "WARN": 3, "ERROR": 4}
    all_findings.sort(key=lambda x: (severity_order.get(x["severity"], 99), x["file"], x["line"]))

    blockers = [f for f in all_findings if f["severity"] == "BLOCKER"]
    highs = [f for f in all_findings if f["severity"] == "HIGH"]
    mediums = [f for f in all_findings if f["severity"] == "MEDIUM"]
    warns = [f for f in all_findings if f["severity"] == "WARN"]
    errors = [f for f in all_findings if f["severity"] == "ERROR"]

    if args.json:
        result = {
            "scanned": files_scanned,
            "findings": all_findings,
            "summary": {
                "blockers": len(blockers),
                "high": len(highs),
                "medium": len(mediums),
                "warnings": len(warns),
                "errors": len(errors),
            },
            "pass": len(all_findings) == 0,
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("  ORION IMPORT AUDIT")
        print(f"  Files scanned: {files_scanned}")
        print(f"{'=' * 60}")

        if not all_findings:
            print("\n  \u2713 No issues found — runtime is clean\n")
            sys.exit(0)

        for f in all_findings:
            icon = {"BLOCKER": "\u2717", "HIGH": "\u26a0", "MEDIUM": "\u2014", "WARN": "\u25b7", "ERROR": "\u2717"}
            print(f"\n  {icon.get(f['severity'], '?')} [{f['severity']}] {f['id']}")
            print(f"      File: {f['file']}:{f['line']}")
            print(f"      {f['message']}")
            if f.get("code"):
                print(f"      Code: {f['code']}")

        print(f"\n{'=' * 60}")
        print(f"  SUMMARY: {len(blockers)} blockers, {len(highs)} high, "
              f"{len(mediums)} medium, {len(warns)} warnings, {len(errors)} errors")
        print(f"{'=' * 60}\n")

    fail = len(blockers) > 0 or len(highs) > 0 or len(errors) > 0
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
