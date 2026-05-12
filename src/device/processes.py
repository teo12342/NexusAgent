"""
Nexus Agent — src/device/processes.py
Cross-platform process management
"""

import os
import sys
import structlog
import psutil
from typing import List, Dict, Optional, Any

logger = structlog.get_logger()
OS_NAME = sys.platform


class ProcessManager:
    """Cross-platform process management."""

    def list_processes(self, sort_by: str = "cpu", limit: int = 50) -> List[Dict]:
        """List running processes sorted by CPU or memory."""
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "exe", "cmdline"]):
            try:
                info = p.info
                info["cpu_pct"] = info.pop("cpu_percent", 0) or 0
                info["mem_pct"] = info.pop("memory_percent", 0) or 0
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if sort_by == "cpu":
            procs.sort(key=lambda x: x["cpu_pct"], reverse=True)
        elif sort_by == "memory":
            procs.sort(key=lambda x: x["mem_pct"], reverse=True)
        elif sort_by == "name":
            procs.sort(key=lambda x: x.get("name", "").lower())

        return [{"pid": p["pid"], "name": p.get("name", ""), "cpu_pct": p["cpu_pct"], "mem_pct": p["mem_pct"], "exe": p.get("exe", "")} for p in procs[:limit]]

    def get_process(self, pid: int) -> Optional[Dict]:
        """Get details for a specific process."""
        try:
            p = psutil.Process(pid)
            return {
                "pid": p.pid,
                "name": p.name(),
                "status": p.status(),
                "cpu_pct": p.cpu_percent(interval=0.1),
                "mem_pct": p.memory_percent(),
                "mem_mb": p.memory_info().rss / (1024**2),
                "exe": p.exe(),
                "cmdline": " ".join(p.cmdline()),
                "create_time": p.create_time(),
                "num_threads": p.num_threads(),
            }
        except psutil.NoSuchProcess:
            return None
        except psutil.AccessDenied:
            return {"error": "access_denied", "pid": pid}

    def get_top_cpu(self, limit: int = 10) -> List[Dict]:
        return self.list_processes(sort_by="cpu", limit=limit)

    def get_top_memory(self, limit: int = 10) -> List[Dict]:
        return self.list_processes(sort_by="memory", limit=limit)

    def kill_process(self, pid: int, force: bool = False) -> Dict:
        """Kill a process."""
        try:
            p = psutil.Process(pid)
            p.kill() if force else p.terminate()
            return {"success": True, "pid": pid, "killed": force}
        except psutil.NoSuchProcess:
            return {"success": False, "error": "process_not_found"}
        except psutil.AccessDenied:
            return {"success": False, "error": "access_denied"}

    def start_process(self, cmdline: str, cwd: str = None) -> Dict:
        """Start a new process."""
        try:
            import subprocess
            parts = cmdline.split()
            proc = subprocess.Popen(parts, cwd=cwd or os.getcwd())
            return {"success": True, "pid": proc.pid, "cmdline": cmdline}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_priority(self, pid: int, priority: str) -> Dict:
        """Set process priority."""
        priority_map = {
            "low": psutil.IDLE_PRIORITY_CLASS if OS_NAME == "win32" else 19,
            "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS if OS_NAME == "win32" else 10,
            "normal": psutil.NORMAL_PRIORITY_CLASS if OS_NAME == "win32" else 0,
            "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS if OS_NAME == "win32" else -5,
            "high": psutil.HIGH_PRIORITY_CLASS if OS_NAME == "win32" else -10,
            "realtime": psutil.REALTIME_PRIORITY_CLASS if OS_NAME == "win32" else -20,
        }
        try:
            p = psutil.Process(pid)
            if OS_NAME == "win32":
                import ctypes
                cls = priority_map.get(priority.lower(), psutil.NORMAL_PRIORITY_CLASS)
                ctypes.windll.kernel32.SetPriorityClass(p.pid, cls)
            else:
                os.nice(priority_map.get(priority.lower(), 0))
            return {"success": True, "pid": pid, "priority": priority}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_processes(self, name: str) -> List[Dict]:
        """Search processes by name."""
        return [p for p in self.list_processes(limit=200) if name.lower() in p.get("name", "").lower()]