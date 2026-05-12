"""
nexus_agent Agent Tools — src/tools/__init__.py
All tool definitions and the tool registry
"""

from typing import Dict, Callable, Any

from .device_tools import register_device_tools
from .memory_tools import register_memory_tools
from .vision_tools import register_vision_tools
from .web_tools import register_web_tools
from .file_tools import register_file_tools

# Global registry: name -> function
TOOL_REGISTRY: Dict[str, Callable] = {}

# Register all tools
register_device_tools(TOOL_REGISTRY)
register_memory_tools(TOOL_REGISTRY)
register_vision_tools(TOOL_REGISTRY)
register_web_tools(TOOL_REGISTRY)
register_file_tools(TOOL_REGISTRY)


__all__ = ["TOOL_REGISTRY"]