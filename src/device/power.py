"""
Nexus Agent — src/device/power.py
Cross-platform power management (shutdown, restart, sleep, lock)
"""

import os
import sys
import structlog
import subprocess
import time
from typing import Dict

logger = structlog.get_logger()
OS_NAME = sys.platform


class PowerControl:
    """Cross-platform power management."""

    def shutdown(self, force: bool = False, timeout: int = 30) -> Dict:
        """Shutdown the machine."""
        try:
            if OS_NAME == "win32":
                flag = "/f" if force else ""
                subprocess.Popen(f"shutdown /s /t {timeout} {flag}".split())
                return {"success": True, "action": "shutdown", "timeout": timeout, "forced": force}
            elif OS_NAME == "linux":
                cmd = ["systemctl", "poweroff"] if not force else ["poweroff"]
                subprocess.Popen(cmd)
                return {"success": True, "action": "shutdown"}
            elif OS_NAME == "darwin":
                subprocess.Popen(["osascript", "-e", "tell application \"System Events\" to shut down"])
                return {"success": True, "action": "shutdown"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def restart(self, force: bool = False, timeout: int = 30) -> Dict:
        """Restart the machine."""
        try:
            if OS_NAME == "win32":
                flag = "/f" if force else ""
                subprocess.Popen(f"shutdown /r /t {timeout} {flag}".split())
                return {"success": True, "action": "restart", "timeout": timeout, "forced": force}
            elif OS_NAME == "linux":
                subprocess.Popen(["reboot"])
                return {"success": True, "action": "restart"}
            elif OS_NAME == "darwin":
                subprocess.Popen(["osascript", "-e", "tell application \"System Events\" to restart"])
                return {"success": True, "action": "restart"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def sleep(self) -> Dict:
        """Put machine to sleep."""
        try:
            if OS_NAME == "win32":
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                return {"success": True, "action": "sleep"}
            elif OS_NAME == "linux":
                subprocess.Popen(["systemctl", "suspend"])
                return {"success": True, "action": "sleep"}
            elif OS_NAME == "darwin":
                subprocess.Popen(["pmset", "sleepnow"])
                return {"success": True, "action": "sleep"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def lock(self) -> Dict:
        """Lock the screen."""
        try:
            if OS_NAME == "win32":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return {"success": True, "action": "lock"}
            elif OS_NAME == "linux":
                # Try multiple lock utilities
                for cmd in [["loginctl", "lock-session"], ["xdg-screensaver", "lock"], ["gnome-screensaver-command", "-l"], ["slock"]]:
                    r = subprocess.run(cmd, capture_output=True)
                    if r.returncode == 0:
                        return {"success": True, "action": "lock", "method": " | ".join(cmd)}
                return {"success": False, "error": "no lock command found"}
            elif OS_NAME == "darwin":
                subprocess.Popen(["/System/Library/CoreServices/Menu Extras/User.menu/Customize.plist"])
                return {"success": True, "action": "lock"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def hibernate(self) -> Dict:
        """Hibernate (Windows/Linux)."""
        if OS_NAME == "win32":
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "hibernate"])
            return {"success": True, "action": "hibernate"}
        elif OS_NAME == "linux":
            subprocess.Popen(["systemctl", "hibernate"])
            return {"success": True, "action": "hibernate"}
        return {"success": False, "error": "unsupported on this OS"}

    def abort_shutdown(self) -> Dict:
        """Abort a pending shutdown."""
        if OS_NAME == "win32":
            subprocess.Popen(["shutdown", "/a"])
            return {"success": True}
        return {"success": True, "action": "not_applicable"}