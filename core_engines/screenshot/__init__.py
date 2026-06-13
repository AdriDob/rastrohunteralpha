"""
screenshot — Screenshot Engine.

Visual evidence translation layer.
Converts pipeline evidence into structured visual representations.
"""

from core_engines.screenshot.engine import (
    AnnotationItem,
    ScreenshotBundle,
    ScreenshotEngine,
    ScreenshotSpec,
    VisualBlock,
)

__all__ = [
    "AnnotationItem",
    "ScreenshotBundle",
    "ScreenshotEngine",
    "ScreenshotSpec",
    "VisualBlock",
]
