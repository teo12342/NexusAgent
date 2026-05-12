"""
Nexus Agent — src/device/__init__.py
Unified cross-platform device API
"""

import sys
import platform
import structlog

logger = structlog.get_logger()

# Detect OS
OS_NAME = sys.platform  # 'win32', 'linux', 'darwin'

from .system import SystemInfo
from .processes import ProcessManager
from .registry import RegistryManager
from .services import ServiceManager
from .power import PowerControl

__all__ = [
    "OS_NAME",
    "SystemInfo",
    "ProcessManager",
    "RegistryManager",
    "ServiceManager",
    "PowerControl",
]