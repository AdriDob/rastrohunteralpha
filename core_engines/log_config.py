import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None, json_output: bool = False) -> None:
    """Configure unified logging across all rastro modules."""
    fmt = "%(asctime)s | %(name)s | %(levelname)-5s | %(message)s"
    if json_output:
        fmt = '{"time":"%(asctime)s","logger":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
    root = logging.getLogger("rastro")
    # Avoid duplicate handlers when desktop/_setup_logging already configured us
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        root.addHandler(handler)
    root.setLevel(level or "INFO")
