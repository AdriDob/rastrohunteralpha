"""
SecLists wordlist profiles for recon and fuzzing operations.
Provides structured access to common SecLists wordlists with
categorization by use case.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

LOG = logging.getLogger("rastro.recon.seclists")


@dataclass
class WordlistProfile:
    """A named wordlist profile with metadata."""
    name: str
    description: str
    relative_path: str
    category: str
    estimated_size: int | None = None
    tags: list[str] = field(default_factory=list)


# Common SecLists wordlists organized by category
WORDLISTS: list[WordlistProfile] = [
    # Discovery / Web Content
    WordlistProfile(
        name="common",
        description="Common web paths (directories and files)",
        relative_path="discovery/Web-Content/common.txt",
        category="web_content",
        estimated_size=4600,
        tags=["directories", "files", "quick"],
    ),
    WordlistProfile(
        name="raft-large-directories",
        description="Large directory wordlist from raft",
        relative_path="discovery/Web-Content/raft-large-directories.txt",
        category="web_content",
        estimated_size=62000,
        tags=["directories", "comprehensive"],
    ),
    WordlistProfile(
        name="raft-large-files",
        description="Large file wordlist from raft",
        relative_path="discovery/Web-Content/raft-large-files.txt",
        category="web_content",
        estimated_size=56000,
        tags=["files", "comprehensive"],
    ),
    WordlistProfile(
        name="api-actions",
        description="Common API action names (lowercase)",
        relative_path="discovery/Web-Content/api/actions-lowercase.txt",
        category="api",
        estimated_size=60,
        tags=["api", "rest"],
    ),
    WordlistProfile(
        name="api-endpoints",
        description="Common API endpoint patterns",
        relative_path="discovery/Web-Content/api/api-endpoints.txt",
        category="api",
        estimated_size=3000,
        tags=["api", "endpoints"],
    ),
    WordlistProfile(
        name="graphql",
        description="GraphQL-related paths and operations",
        relative_path="discovery/Web-Content/graphql.txt",
        category="api",
        estimated_size=200,
        tags=["api", "graphql"],
    ),
    WordlistProfile(
        name="swagger-endpoints",
        description="Swagger/OpenAPI endpoint patterns",
        relative_path="discovery/Web-Content/swagger.txt",
        category="api",
        estimated_size=100,
        tags=["api", "swagger", "openapi"],
    ),

    # Admin panels
    WordlistProfile(
        name="admin-panels",
        description="Common admin panel paths",
        relative_path="discovery/Web-Content/admin-panels.txt",
        category="admin",
        estimated_size=500,
        tags=["admin", "login", "dashboard"],
    ),

    # Backups
    WordlistProfile(
        name="backups",
        description="Common backup file patterns",
        relative_path="discovery/Web-Content/backups.txt",
        category="sensitive",
        estimated_size=300,
        tags=["backup", "sensitive"],
    ),

    # Subdomains
    WordlistProfile(
        name="subdomains-top1million-5000",
        description="Top 5000 subdomains from 1M domains",
        relative_path="discovery/DNS/subdomains-top1million-5000.txt",
        category="dns",
        estimated_size=5000,
        tags=["subdomains", "dns", "quick"],
    ),
    WordlistProfile(
        name="subdomains-top1million-20000",
        description="Top 20000 subdomains from 1M domains",
        relative_path="discovery/DNS/subdomains-top1million-20000.txt",
        category="dns",
        estimated_size=20000,
        tags=["subdomains", "dns", "balanced"],
    ),

    # Parameters
    WordlistProfile(
        name="burp-params",
        description="Common parameter names from Burp Suite",
        relative_path="discovery/Web-Content/burp-parameter-names.txt",
        category="parameters",
        estimated_size=2500,
        tags=["params", "fuzzing"],
    ),

    # Passwords (for login form testing)
    WordlistProfile(
        name="common-passwords",
        description="Top 10000 common passwords",
        relative_path="Passwords/Common-Credentials/10k-most-common.txt",
        category="passwords",
        estimated_size=10000,
        tags=["auth", "passwords"],
    ),
]

# Fast lookup structures
_BY_NAME: dict[str, WordlistProfile] = {wl.name: wl for wl in WORDLISTS}
_BY_CATEGORY: dict[str, list[WordlistProfile]] = {}
for wl in WORDLISTS:
    _BY_CATEGORY.setdefault(wl.category, []).append(wl)


def get_wordlist(name: str) -> WordlistProfile | None:
    """Get a wordlist profile by name."""
    return _BY_NAME.get(name)


def get_wordlists_by_category(category: str) -> list[WordlistProfile]:
    """Get all wordlists in a category."""
    return _BY_CATEGORY.get(category, [])


def resolve_path(
    profile: WordlistProfile, seclists_dir: str = "/usr/share/seclists"
) -> Path | None:
    """Resolve the absolute path to a wordlist file."""
    candidate = Path(seclists_dir) / profile.relative_path
    if candidate.exists():
        return candidate
    LOG.debug("Wordlist not found: %s", candidate)
    return None


def available_wordlists(seclists_dir: str = "/usr/share/seclists") -> list[str]:
    """Return names of wordlists that exist on disk."""
    available = []
    for wl in WORDLISTS:
        if resolve_path(wl, seclists_dir):
            available.append(wl.name)
    return available


def get_recommended_profiles(mode: str) -> list[str]:
    """Get recommended wordlist names for a scan mode."""
    mode_map = {
        "FAST": ["common", "subdomains-top1million-5000"],
        "BALANCED": [
            "common",
            "admin-panels",
            "api-actions",
            "subdomains-top1million-20000",
            "burp-params",
        ],
        "DEEP": [
            "raft-large-directories",
            "raft-large-files",
            "api-endpoints",
            "admin-panels",
            "backups",
            "subdomains-top1million-20000",
            "burp-params",
            "common-passwords",
            "graphql",
            "swagger-endpoints",
        ],
    }
    return mode_map.get(mode.upper(), [])
