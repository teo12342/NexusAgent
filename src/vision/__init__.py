"""
nexus_agent Agent Vision — src/vision/__init__.py
Native vision: screenshot capture, screen analysis, click detection
"""

from .capture import ScreenCapture
from .analyzer import ScreenAnalyzer

__all__ = ["ScreenCapture", "ScreenAnalyzer"]