"""
Nexus Agent — src/device/registry.py
Cross-platform registry/config management
"""

import os
import sys
import structlog
import json
from typing import Dict, List, Optional, Any

logger = structlog.get_logger()
OS_NAME = sys.platform


class RegistryManager:
    """Cross-platform registry/configuration management.

    On Windows: uses winreg for real registry.
    On Linux/macOS: uses flat JSON files in ~/.nexus_agent/ as equivalent.
    """

    def __init__(self):
        self.config_dir = os.path.expanduser("~/.nexus_agent")
        os.makedirs(self.config_dir, exist_ok=True)
        self._winreg = None
        if OS_NAME == "win32":
            try:
                import winreg
                self._winreg = winreg
            except ImportError:
                logger.warning("winreg_not_available")

    def _config_file(self, key: str) -> str:
        safe = key.replace("\\", "_").replace("/", "_")
        return os.path.join(self.config_dir, f"{safe}.json")

    # ---- Windows Registry ----
    def _read_winreg(self, hive: str, subkey: str, value_name: str = None):
        """Read from Windows registry."""
        if not self._winreg:
            return {"error": "winreg unavailable"}
        hmap = {"HKEY_LOCAL_MACHINE": self._winreg.HKEY_LOCAL_MACHINE, "HKEY_CURRENT_USER": self._winreg.HKEY_CURRENT_USER}
        h = hmap.get(hive, self._winreg.HKEY_CURRENT_USER)
        try:
            with self._winreg.OpenKey(h, subkey, 0, self._winreg.KEY_READ) as k:
                if value_name:
                    val, typ = self._winreg.QueryValueEx(k, value_name)
                    return {"value": val, "type": typ}
                else:
                    result = {}
                    i = 0
                    while True:
                        try:
                            n, v, t = self._winreg.EnumValue(k, i)
                            result[n] = {"value": v, "type": t}
                            i += 1
                        except OSError:
                            break
                    return result
        except FileNotFoundError:
            return {"error": "key_not_found"}
        except Exception as e:
            return {"error": str(e)}

    def _write_winreg(self, hive: str, subkey: str, value_name: str, data: Any, vtype: str = "REG_SZ"):
        if not self._winreg:
            return {"error": "winreg unavailable"}
        hmap = {"HKEY_LOCAL_MACHINE": self._winreg.HKEY_LOCAL_MACHINE, "HKEY_CURRENT_USER": self._winreg.HKEY_CURRENT_USER}
        h = hmap.get(hive, self._winreg.HKEY_CURRENT_USER)
        tmap = {"REG_SZ": self._winreg.REG_SZ, "REG_DWORD": self._winreg.REG_DWORD, "REG_BINARY": self._winreg.REG_BINARY}
        try:
            with self._winreg.CreateKey(h, subkey) as k:
                self._winreg.SetValueEx(k, value_name, 0, tmap.get(vtype, self._winreg.REG_SZ), data)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    # ---- Cross-platform API ----
    def list_subkeys(self, hive: str = None, subkey: str = None) -> Dict:
        """List subkeys/values. On non-Windows, uses JSON config files."""
        if OS_NAME == "win32" and hive:
            return self._read_winreg(hive, subkey or "")
        # Non-Windows: use JSON config files
        cfg = {}
        for f in os.listdir(self.config_dir):
            if f.endswith(".json"):
                with open(os.path.join(self.config_dir, f)) as fp:
                    cfg[f[:-5]] = json.load(fp)
        return {"config_files": list(cfg.keys()), "config_dir": self.config_dir}

    def read_value(self, hive: str, subkey: str, value_name: str) -> Dict:
        if OS_NAME == "win32":
            return self._read_winreg(hive, subkey, value_name)
        return {"error": "use config files on non-Windows"}

    def write_value(self, hive: str, subkey: str, value_name: str, data: Any, value_type: str = "REG_SZ") -> Dict:
        if OS_NAME == "win32":
            return self._write_winreg(hive, subkey, value_name, data, value_type)
        # Non-Windows: JSON config
        fpath = self._config_file(subkey or value_name)
        try:
            with open(fpath) as fp:
                store = json.load(fp)
        except (FileNotFoundError, json.JSONDecodeError):
            store = {}
        store[value_name] = data
        with open(fpath, "w") as fp:
            json.dump(store, fp, indent=2)
        return {"success": True, "file": fpath}

    def get_startup_items(self) -> List[Dict]:
        """Get startup items across all platforms."""
        items = []
        if OS_NAME == "win32":
            try:
                import winreg
                paths = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                ]
                for h, key in paths:
                    try:
                        with winreg.OpenKey(h, key, 0, winreg.KEY_READ) as k:
                            i = 0
                            while True:
                                try:
                                    n, v, _ = winreg.EnumValue(k, i)
                                    items.append({"name": n, "path": v, "source": key, "hive": str(h)})
                                    i += 1
                                except OSError:
                                    break
                    except FileNotFoundError:
                        pass
            except Exception as e:
                logger.warning("startup_read_error", error=str(e))
        elif OS_NAME == "linux":
            autostart = os.path.expanduser("~/.config/autostart")
            if os.path.exists(autostart):
                for f in os.listdir(autostart):
                    if f.endswith(".desktop"):
                        items.append({"name": f, "source": "autostart", "file": os.path.join(autostart, f)})
            # systemd user
            try:
                import subprocess
                r = subprocess.run(["systemctl", "--user", "list-unit-files", "--no-pager"], capture_output=True, text=True)
                for line in r.stdout.split("\n"):
                    if "enabled" in line:
                        parts = line.split()
                        if parts:
                            items.append({"name": parts[0], "source": "systemd"})
            except Exception:
                pass
        elif OS_NAME == "darwin":
            # LaunchAgents
            lg = os.path.expanduser("~/Library/LaunchAgents")
            if os.path.exists(lg):
                for f in os.listdir(lg):
                    if f.endswith(".plist"):
                        items.append({"name": f, "source": "LaunchAgents", "file": os.path.join(lg, f)})
        return items

    def add_to_startup(self, app_name: str, exe_path: str) -> Dict:
        """Add app to startup items."""
        if OS_NAME == "win32":
            return self.write_value("HKEY_CURRENT_USER", r"Software\Microsoft\Windows\CurrentVersion\Run", app_name, exe_path)
        elif OS_NAME == "linux":
            desktop = os.path.expanduser(f"~/.config/autostart/{app_name}.desktop")
            content = f"[Desktop Entry]\nType=Application\nName={app_name}\nExec={exe_path}\nX-GNOME-Autostart-enabled=true\n"
            os.makedirs(os.path.dirname(desktop), exist_ok=True)
            with open(desktop, "w") as f:
                f.write(content)
            return {"success": True, "file": desktop}
        elif OS_NAME == "darwin":
            plist = os.path.expanduser(f"~/Library/LaunchAgents/{app_name}.plist")
            content = f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">\n<plist version="1.0">\n<dict>\n<key>Label</key><string>{app_name}</string>\n<key>ProgramArguments</key><array><string>{exe_path}</string></array>\n<key>RunAtLoad</key><true/>\n</dict>\n</plist>'
            os.makedirs(os.path.dirname(plist), exist_ok=True)
            with open(plist, "w") as f:
                f.write(content)
            return {"success": True, "file": plist}

    def remove_from_startup(self, app_name: str) -> Dict:
        if OS_NAME == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
                winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
                return {"success": True}
            except FileNotFoundError:
                return {"success": False, "error": "not_found"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        elif OS_NAME == "linux":
            desktop = os.path.expanduser(f"~/.config/autostart/{app_name}.desktop")
            if os.path.exists(desktop):
                os.remove(desktop)
                return {"success": True}
            return {"success": False, "error": "not_found"}
        elif OS_NAME == "darwin":
            plist = os.path.expanduser(f"~/Library/LaunchAgents/{app_name}.plist")
            if os.path.exists(plist):
                os.remove(plist)
                return {"success": True}
            return {"success": False, "error": "not_found"}