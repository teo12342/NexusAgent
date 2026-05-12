"""
Nexus Agent — src/device/services.py
Cross-platform service/daemon management
"""

import os
import sys
import structlog
import subprocess
from typing import List, Dict, Optional

logger = structlog.get_logger()
OS_NAME = sys.platform


class ServiceManager:
    """Cross-platform service/daemon management.

    Windows: real service control via psutil /servicemanager
    Linux: systemd (systemctl), OpenRC (rc-service), or sysvinit
    macOS: launchd (launchctl)
    """

    def list_services(self, state: str = "all") -> List[Dict]:
        """List services/daemons."""
        if OS_NAME == "win32":
            return self._list_win_services(state)
        elif OS_NAME == "linux":
            return self._list_linux_services(state)
        elif OS_NAME == "darwin":
            return self._list_macos_services(state)
        return []

    def _list_win_services(self, state: str = "all") -> List[Dict]:
        try:
            import win32serviceutil, win32service
            # Use sc.exe for cross-python compatibility
            result = subprocess.run(["sc", "query", "state=", "all"], capture_output=True, text=True, shell=True)
            services = []
            current = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("SERVICE_NAME"):
                    if current:
                        services.append(current)
                    current = {"name": line.split(":")[1].strip(), "type": "", "state": ""}
                elif line.startswith("TYPE"):
                    current["type"] = line.split(":")[1].strip()
                elif line.startswith("STATE"):
                    current["state"] = line.split(":")[1].strip().split()[0]
            if current:
                services.append(current)

            if state == "running":
                return [s for s in services if s.get("state") == "RUNNING"]
            elif state == "stopped":
                return [s for s in services if s.get("state") == "STOPPED"]
            return services
        except Exception as e:
            logger.warning("win_services_error", error=str(e))
            return []

    def _list_linux_services(self, state: str = "all") -> List[Dict]:
        services = []
        # Try systemctl first
        try:
            r = subprocess.run(["systemctl", "list-unit-files", "--no-pager", "--type=service"], capture_output=True, text=True, timeout=10)
            for line in r.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0].replace(".service", "")
                    services.append({
                        "name": name,
                        "state": parts[1] if len(parts) > 1 else "unknown",
                        "source": "systemd",
                    })
        except Exception:
            pass

        # OpenRC
        try:
            r = subprocess.run(["rc-service", "--list"], capture_output=True, text=True, timeout=5)
            for name in r.stdout.split():
                services.append({"name": name.strip(), "state": "unknown", "source": "openrc"})
        except Exception:
            pass

        if state == "running":
            return [s for s in services if s.get("state") in ("active", "started", "running")]
        elif state == "stopped":
            return [s for s in services if s.get("state") in ("stopped", "inactive", "disabled")]
        return services

    def _list_macos_services(self, state: str = "all") -> List[Dict]:
        services = []
        try:
            r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10)
            for line in r.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 3:
                    services.append({"name": parts[2], "pid": parts[0] if parts[0] != "-" else None, "state": "running" if parts[0] != "-" else "stopped"})
        except Exception as e:
            logger.warning("macos_services_error", error=str(e))
        return services

    def start_service(self, service_name: str) -> Dict:
        if OS_NAME == "win32":
            try:
                subprocess.run(["sc", "start", service_name], capture_output=True, check=True)
                return {"success": True, "service": service_name}
            except Exception as e:
                return {"success": False, "error": str(e)}
        elif OS_NAME == "linux":
            for cmd in [["systemctl", "start", service_name], ["rc-service", service_name, "start"]]:
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    return {"success": True, "service": service_name, "method": "systemctl"}
                except Exception:
                    pass
            return {"success": False, "error": "service not found"}
        elif OS_NAME == "darwin":
            try:
                subprocess.run(["launchctl", "load", f"/Library/LaunchDaemons/{service_name}.plist"], capture_output=True, check=True)
                return {"success": True, "service": service_name}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def stop_service(self, service_name: str) -> Dict:
        if OS_NAME == "win32":
            try:
                subprocess.run(["sc", "stop", service_name], capture_output=True, check=True)
                return {"success": True, "service": service_name}
            except Exception as e:
                return {"success": False, "error": str(e)}
        elif OS_NAME == "linux":
            for cmd in [["systemctl", "stop", service_name], ["rc-service", service_name, "stop"]]:
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    return {"success": True, "service": service_name}
                except Exception:
                    pass
            return {"success": False, "error": "service not found"}
        elif OS_NAME == "darwin":
            try:
                subprocess.run(["launchctl", "unload", f"/Library/LaunchDaemons/{service_name}.plist"], capture_output=True, check=True)
                return {"success": True, "service": service_name}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "unsupported OS"}

    def restart_service(self, service_name: str) -> Dict:
        r = self.stop_service(service_name)
        if r.get("success"):
            import time; time.sleep(1)
            return self.start_service(service_name)
        return r

    def service_status(self, service_name: str) -> Dict:
        if OS_NAME == "win32":
            try:
                r = subprocess.run(["sc", "query", service_name], capture_output=True, text=True)
                output = r.stdout
                if "STOPPED" in output:
                    return {"name": service_name, "state": "stopped"}
                elif "RUNNING" in output:
                    return {"name": service_name, "state": "running"}
                return {"name": service_name, "state": "unknown", "raw": output[:200]}
            except Exception as e:
                return {"error": str(e)}
        elif OS_NAME == "linux":
            try:
                r = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
                return {"name": service_name, "state": r.stdout.strip()}
            except Exception:
                return {"name": service_name, "state": "unknown"}
        return {"name": service_name, "state": "unsupported"}