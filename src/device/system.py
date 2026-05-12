"""
Nexus Agent — src/device/system.py
Cross-platform system info (CPU, RAM, disk, network, battery)
"""

import os
import sys
import platform
import structlog
import time
import psutil
from typing import Dict, List, Any, Optional

logger = structlog.get_logger()

OS_NAME = sys.platform  # 'win32', 'linux', 'darwin'


class SystemInfo:
    """Cross-platform system stats."""

    def __init__(self):
        self.hostname = platform.node()
        self.os_name = OS_NAME
        self._last_net = None
        self._last_net_time = None
        self._last_net_received = 0
        self._last_net_sent = 0

    def get_full_stats(self) -> Dict[str, Any]:
        """Get all system stats in one call."""
        cpu = self._get_cpu()
        mem = self._get_memory()
        disks = self._get_disks()
        net = self._get_network()
        battery = self._get_battery()
        uptime = self._get_uptime()
        return {
            "hostname": self.hostname,
            "platform": {"os": self.os_name, "release": platform.release()},
            "cpu": cpu,
            "memory": mem,
            "disks": disks,
            "network": net,
            "battery": battery,
            "uptime": uptime,
            "cpu_count_logical": os.cpu_count(),
            "cpu_count_physical": psutil.cpu_count(logical=False) if OS_NAME != "darwin" else psutil.cpu_count(),
        }

    def _get_cpu(self) -> Dict:
        try:
            return {
                "count": psutil.cpu_count(),
                "percent_per_core": psutil.cpu_percent(interval=0.1, percpu=True),
                "overall_percent": psutil.cpu_percent(interval=0.5),
                "freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            }
        except Exception as e:
            logger.warning("cpu_stat_error", error=str(e))
            return {"percent": 0, "cores": []}

    def _get_memory(self) -> Dict:
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total_gb": round(vm.total / (1024**3), 2),
                "available_gb": round(vm.available / (1024**3), 2),
                "used_gb": round(vm.used / (1024**3), 2),
                "percent": vm.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percent": swap.percent,
            }
        except Exception as e:
            logger.warning("memory_stat_error", error=str(e))
            return {}

    def _get_disks(self) -> List[Dict]:
        try:
            partitions = psutil.disk_partitions()
            result = []
            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    result.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                    })
                except PermissionError:
                    continue
            return result
        except Exception as e:
            logger.warning("disk_stat_error", error=str(e))
            return []

    def _get_network(self) -> Dict:
        try:
            net = psutil.net_io_counters()
            now = time.time()
            if self._last_net is not None:
                elapsed = now - self._last_net_time
                recv_mb = (net.bytes_recv - self._last_net_received) / (1024**2) / max(elapsed, 0.001)
                sent_mb = (net.bytes_sent - self._last_net_sent) / (1024**2) / max(elapsed, 0.001)
            else:
                recv_mb, sent_mb = 0, 0

            self._last_net = net
            self._last_net_time = now
            self._last_net_received = net.bytes_recv
            self._last_net_sent = net.bytes_sent

            perNic = {}
            for iface, addrs in psutil.net_if_addrs().items():
                try:
                    n = psutil.net_io_counters(pernic=True).get(iface)
                    if n:
                        perNic[iface] = {"bytes_sent": n.bytes_sent, "bytes_recv": n.bytes_recv}
                except Exception:
                    pass

            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "speed_mbps": round(recv_mb * 8 + sent_mb * 8, 2),
                "per_nic": perNic,
            }
        except Exception as e:
            logger.warning("network_stat_error", error=str(e))
            return {}

    def _get_battery(self) -> Optional[Dict]:
        if OS_NAME != "linux":
            return None
        try:
            import subprocess
            out = subprocess.run(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"], capture_output=True, text=True)
            lines = out.stdout.split("\n")
            data = {}
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip()
            if data.get("state") == "charging":
                return {"present": True, "percent": float(data.get("percentage", 0)), "charging": True}
            elif data.get("state") == "discharging":
                return {"present": True, "percent": float(data.get("percentage", 0)), "charging": False, "time_left": data.get("time to empty")}
            return {"present": True, "percent": float(data.get("percentage", 0))}
        except Exception:
            pass

        try:
            bat = psutil.sensors_battery()
            if bat:
                return {"present": True, "percent": bat.percent, "charging": bat.power_plugged}
        except Exception:
            pass
        return None

    def _get_uptime(self) -> Dict:
        try:
            boot = psutil.boot_time()
            uptime_s = time.time() - boot
            h = int(uptime_s // 3600)
            m = int((uptime_s % 3600) // 60)
            return {
                "seconds": int(uptime_s),
                "human": f"{h}h {m}m",
                "boot_time": boot,
            }
        except Exception as e:
            logger.warning("uptime_error", error=str(e))
            return {}

    def get_uptime_human(self) -> str:
        u = self._get_uptime()
        return u.get("human", "unknown")