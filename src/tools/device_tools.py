"""Device tools for nexus_agent Agent — system, process, registry, services, power."""

import psutil
import structlog
from typing import Dict, Any

logger = structlog.get_logger()


def register_device_tools(registry: Dict):
    # Lazy import to avoid circular
    from ..device import DeviceSystem, ProcessManager, RegistryManager, ServiceManager, PowerControl

    device_system = DeviceSystem()
    process_manager = ProcessManager()
    registry_manager = RegistryManager()
    service_manager = ServiceManager()
    power_control = PowerControl()

    def get_system_stats() -> Dict[str, Any]:
        return device_system.get_full_stats()

    def get_processes(sort_by: str = "cpu", limit: int = 30) -> list:
        return process_manager.list_processes(sort_by=sort_by, limit=limit)

    def get_top_cpu(limit: int = 10) -> list:
        return process_manager.get_top_cpu(limit=limit)

    def get_top_memory(limit: int = 10) -> list:
        return process_manager.get_top_memory(limit=limit)

    def kill_process(pid: int, force: bool = False) -> Dict:
        return process_manager.kill_process(pid=pid, force=force)

    def start_process(cmdline: str, cwd: str = None) -> Dict:
        return process_manager.start_process(cmdline=cmdline, cwd=cwd)

    def set_process_priority(pid: int, priority: str) -> Dict:
        return process_manager.set_priority(pid=pid, priority=priority)

    def get_registry(hive: str, subkey: str) -> Dict:
        return registry_manager.list_subkeys(hive=hive, subkey=subkey)

    def set_registry_value(hive: str, subkey: str, value: str, data: Any, vtype: str = "REG_SZ") -> Dict:
        return registry_manager.write_value(hive=hive, subkey=subkey, value_name=value, data=data, value_type=vtype)

    def get_startup_items() -> list:
        return registry_manager.get_startup_items()

    def add_to_startup(app_name: str, exe_path: str) -> Dict:
        return registry_manager.add_to_startup(app_name=app_name, exe_path=exe_path)

    def remove_from_startup(app_name: str) -> Dict:
        return registry_manager.remove_from_startup(app_name=app_name)

    def list_services(state: str = "all") -> list:
        return service_manager.list_services(state=state)

    def start_service(service_name: str) -> Dict:
        return service_manager.start_service(service_name=service_name)

    def stop_service(service_name: str) -> Dict:
        return service_manager.stop_service(service_name=service_name)

    def restart_service(service_name: str) -> Dict:
        return service_manager.restart_service(service_name=service_name)

    def shutdown_pc(force: bool = False, timeout: int = 30) -> Dict:
        return power_control.shutdown(force=force, timeout=timeout)

    def restart_pc(force: bool = False, timeout: int = 30) -> Dict:
        return power_control.restart(force=force, timeout=timeout)

    def sleep_pc() -> Dict:
        return power_control.sleep()

    def lock_pc() -> Dict:
        return power_control.lock()

    def abort_shutdown() -> Dict:
        return power_control.abort_shutdown()

    # Register all
    tools = {
        "system_stats": get_system_stats,
        "get_processes": get_processes,
        "top_cpu": get_top_cpu,
        "top_memory": get_top_memory,
        "kill_process": kill_process,
        "start_process": start_process,
        "set_process_priority": set_process_priority,
        "get_registry": get_registry,
        "set_registry_value": set_registry_value,
        "get_startup_items": get_startup_items,
        "add_to_startup": add_to_startup,
        "remove_from_startup": remove_from_startup,
        "list_services": list_services,
        "start_service": start_service,
        "stop_service": stop_service,
        "restart_service": restart_service,
        "shutdown_pc": shutdown_pc,
        "restart_pc": restart_pc,
        "sleep_pc": sleep_pc,
        "lock_pc": lock_pc,
        "abort_shutdown": abort_shutdown,
    }
    registry.update(tools)