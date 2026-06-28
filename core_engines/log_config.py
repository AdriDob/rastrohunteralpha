import logging
import sys

PREFIX_MAP: dict[str, str] = {
    "rastro.identity_vault":    "[VAULT]",
    "rastro.identity":          "[IDENTITY]",
    "rastro.auth":              "[AUTH]",
    "rastro.license":           "[LICENSE]",
    "rastro.hardware":          "[HW]",
    "rastro.pipeline":          "[PIPELINE]",
    "rastro.report":            "[REPORT]",
    "rastro.reporting":         "[REPORT]",
    "rastro.ai":                "[AI]",
    "rastro.assistant":         "[AI]",
    "rastro.intelligence":      "[INTEL]",
    "rastro.learning":          "[LEARN]",
    "rastro.memory":            "[MEMORY]",
    "rastro.finance":           "[FINANCE]",
    "rastro.roi":               "[FINANCE]",
    "rastro.sync":              "[SYNC]",
    "rastro.build":             "[BUILD]",
    "rastro.desktop":           "[DESKTOP]",
    "rastro.updater":           "[UPDATE]",
    "rastro.ws":                "[WS]",
    "rastro.events":            "[EVENTS]",
    "rastro.orchestrator":      "[ORCH]",
    "rastro.observability":     "[OBS]",
    "rastro.recon":             "[RECON]",
    "rastro.validation":        "[VALIDATE]",
    "rastro.evidence":          "[EVIDENCE]",
    "rastro.notifications":     "[NOTIFY]",
    "rastro.opportunity":       "[OPPORTUNITY]",
    "rastro.targets":           "[TARGET]",
    "rastro.engine":            "[ENGINE]",
    "rastro.execution":         "[EXEC]",
    "rastro.analysis":          "[ANALYSIS]",
    "rastro.attack":            "[ATTACK]",
    "rastro.explainability":    "[EXPLAIN]",
    "rastro.contracts":         "[CONTRACT]",
    "rastro.fallback":          "[FALLBACK]",
    "rastro.confidence":        "[CONFIDENCE]",
    "rastro.product_rules":     "[RULES]",
    "rastro.system_state":      "[STATE]",
    "rastro.system_health":     "[HEALTH]",
    "rastro.timeline":          "[TIMELINE]",
    "rastro.screenshot":        "[SCREENSHOT]",
    "rastro.web3":              "[WEB3]",
    "rastro.quick_wins":        "[QUICKWIN]",
    "rastro.ux":                "[UX]",
    "rastro.accountability":    "[ACCT]",
    "rastro.review_queue":      "[REVIEW]",
    "rastro.gateway":           "[GATEWAY]",
    "rastro.platform":          "[PLATFORM]",
    "rastro.unification":       "[UNIFY]",
    "rastro.clustering":        "[CLUSTER]",
    "rastro.differential":      "[DIFF]",
    "rastro.target_auth":       "[AUTH]",
    "rastro.serve":             "[SERVE]",
}


class PrefixedFormatter(logging.Formatter):
    """Log formatter that injects structured prefixes based on logger name.

    Uses longest-prefix-match: for ``rastro.auth.manager`` it will match
    ``rastro.auth`` (not just exact ``record.name`` lookups).
    """

    def format(self, record: logging.LogRecord) -> str:
        prefix = ""
        name = record.name
        # Longest-prefix match
        for key, value in PREFIX_MAP.items():
            if name.startswith(key) and len(key) > len(prefix):
                prefix = value
        record.prefix = prefix
        return super().format(record)


def setup_logging(level: str | None = None, json_output: bool = False) -> None:
    """Configure unified logging across all rastro modules."""
    if json_output:
        fmt = '{"time":"%(asctime)s","prefix":"%(prefix)s","logger":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
    else:
        fmt = "%(asctime)s %(prefix)-12s | %(levelname)-5s | %(message)s"
    root = logging.getLogger("rastro")
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(PrefixedFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        root.addHandler(handler)
    root.setLevel(level or "INFO")
