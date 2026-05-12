"""
nexus_agent Agent Dashboard — src/dashboard/__init__.py
Flask web dashboard with WebSocket support
"""

from .app import create_app

__all__ = ["create_app"]