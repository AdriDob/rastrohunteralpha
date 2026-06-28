"""Project Dashboard API — internal project status, metrics, and governance data.

Reads from:
  - project_management/*.md (PROJECT_STATUS, TIMELINE, FEATURE_MATRIX, TECH_DEBT)
  - git (latest commit, tag, branch)
  - local test runner (test count)
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/project-dashboard", tags=["project-dashboard"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PM_DIR = PROJECT_ROOT / "project_management"


# ─── Helpers ─────────────────────────────────────────────────────────────

def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def _read_md(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _count_tests() -> dict[str, Any]:
    try:
        r = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60,
        )
        out = r.stdout.strip()
        m = re.search(r"(\d+) passed", out)
        passed = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) failed", out)
        failed = int(m.group(1)) if m else 0
        return {"passed": passed, "failed": failed, "total": passed + failed}
    except Exception as e:
        return {"passed": 0, "failed": 0, "total": 0, "error": str(e)}


# ─── Endpoints ───────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary() -> dict[str, Any]:
    """Quick overview: version, git, tests, overall progress."""
    version = _read_md(PROJECT_ROOT / "VERSION").strip() or "0.0.0"

    commit = _run(["git", "log", "--oneline", "-1"])
    tag = _run(["git", "describe", "--tags", "--always"])
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    tests = _count_tests()

    # Read PROJECT_STATUS for progress percentages
    status_raw = _read_md(PM_DIR / "PROJECT_STATUS.md")
    progress = {}
    for line in status_raw.splitlines():
        m = re.match(r"\|\s*\*\*(\w+)\*\*\s*\|\s*(\d+)%\s*\|", line)
        if m:
            progress[m.group(1).lower()] = int(m.group(2))
        m2 = re.match(r"\|\s*(\w+)\s*\|\s*(\d+)%\s*\|", line)
        if m2:
            key = m2.group(1).lower()
            if key not in ("dimensión", "progreso", "dimensi"):
                progress[key] = int(m2.group(2))

    overall = progress.get("testing", 0)
    if progress:
        vals = [v for v in progress.values() if isinstance(v, int)]
        if vals:
            overall = sum(vals) // len(vals)

    return {
        "version": version,
        "commit": commit,
        "tag": tag,
        "branch": branch,
        "tests": tests,
        "overall_progress": overall,
        "progress_by_area": progress,
    }


@router.get("/git")
def get_git_log() -> dict[str, Any]:
    log = _run(["git", "log", "--oneline", "-10"])
    lines = [line.strip() for line in log.split("\n") if line.strip()] if log else []
    return {
        "commit": _run(["git", "log", "--oneline", "-1"]),
        "tag": _run(["git", "describe", "--tags", "--always"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "log": lines,
    }


@router.get("/tests")
def get_test_status() -> dict[str, Any]:
    return _count_tests()


@router.get("/feature-matrix")
def get_feature_matrix() -> list[dict[str, str]]:
    raw = _read_md(PM_DIR / "FEATURE_MATRIX.md")
    rows = []
    current_section = ""
    for line in raw.splitlines():
        sm = re.match(r"^## (.+)", line)
        if sm:
            current_section = sm.group(1).strip()
            continue
        tm = re.match(r"^\| (.+) \| (.+) \| (.+) \| (.+) \| (.+) \|", line)
        if tm and tm.group(1) not in ("Feature", "---------"):
            rows.append({
                "feature": tm.group(1).strip(),
                "status": tm.group(2).strip(),
                "dependencies": tm.group(3).strip(),
                "priority": tm.group(4).strip(),
                "impact": tm.group(5).strip(),
                "section": current_section,
            })
    return rows


@router.get("/tech-debt")
def get_tech_debt() -> dict[str, Any]:
    items = {"high": [], "medium": [], "low": []}
    raw = _read_md(PM_DIR / "TECH_DEBT.md")
    current_priority = "medium"
    for line in raw.splitlines():
        pm = re.match(r"^## (🔴|🟡|🟢) (.+)", line)
        if pm:
            icon = pm.group(1)
            if "🔴" in icon:
                current_priority = "high"
            elif "🟡" in icon:
                current_priority = "medium"
            else:
                current_priority = "low"
            continue
        tm = re.match(r"^\| (.+) \| (.+) \| (.+) \|", line)
        if tm and tm.group(1) not in ("Item", "------"):
            items.setdefault(current_priority, []).append({
                "item": tm.group(1).strip(),
                "file": tm.group(2).strip(),
                "description": tm.group(3).strip(),
            })
    return items


@router.get("/timeline")
def get_timeline() -> list[dict[str, str]]:
    raw = _read_md(PM_DIR / "TIMELINE.md")
    versions = []
    current_version = ""
    current_state = ""
    for line in raw.splitlines():
        vm = re.match(r"^## (🟢|🔵) (v[\d.]+) (.+)", line)
        if vm:
            icon = vm.group(1)
            current_version = vm.group(2)
            current_state = "done" if "🟢" in icon else "in_progress" if "🔵" in icon else "planned"
            versions.append({
                "version": current_version,
                "title": vm.group(3).strip(),
                "state": current_state,
            })
            continue
        sm = re.match(r"^\*\*Estado:\*\* (.+)", line)
        if sm:
            state_raw = sm.group(1).strip().lower()
            if "archived" in state_raw or "released" in state_raw:
                current_state = "done"
            elif "in progress" in state_raw:
                current_state = "in_progress"
            elif "planned" in state_raw:
                current_state = "planned"
            if versions:
                versions[-1]["state"] = current_state
            continue
        dm = re.match(r"^\*\*Tag:\*\* (.+)", line)
        if dm and versions:
            versions[-1]["tag"] = dm.group(1).strip()
        cm = re.match(r"^\*\*Commit:\*\* (.+)", line)
        if cm and versions:
            versions[-1]["commit_ref"] = cm.group(1).strip()
    return versions


@router.get("/architecture-tree")
def get_architecture_tree() -> dict[str, Any]:
    """Return summarized project tree for developer mode."""
    return {
        "root": PROJECT_ROOT.name,
        "directories": sorted([
            d.name for d in PROJECT_ROOT.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in ("__pycache__", "node_modules", ".venv", "dist", ".git")
        ]),
        "routers": sorted([
            f.stem for f in (PROJECT_ROOT / "api" / "routers").iterdir()
            if f.suffix == ".py" and not f.name.startswith("_")
        ]),
        "core_engines": sorted([
            d.name for d in (PROJECT_ROOT / "core_engines").iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]),
        "frontend_pages": sorted([
            f.stem for f in (PROJECT_ROOT / "frontend" / "src" / "pages").iterdir()
            if f.suffix in (".tsx", ".ts") and not f.name.startswith("_")
        ]),
    }
