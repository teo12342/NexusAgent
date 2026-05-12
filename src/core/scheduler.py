"""
nexus_agent Agent Scheduler — src/core/scheduler.py
Periodic tasks and cron-like scheduling
"""

import time
import threading
import croniter
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class ScheduleType(Enum):
    INTERVAL = "interval"      # Every N seconds
    CRON = "cron"              # Cron expression
    ONCE = "once"              # Run once at specific time


@dataclass
class ScheduledTask:
    id: str
    name: str
    func: Callable
    schedule_type: ScheduleType
    interval_seconds: Optional[float] = None
    cron_expr: Optional[str] = None
    run_at: Optional[float] = None
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    metadata: Any = None

    def should_run(self, now: float) -> bool:
        if not self.enabled:
            return False
        if self.schedule_type == ScheduleType.ONCE:
            return self.run_at and now >= self.run_at
        if self.schedule_type == ScheduleType.INTERVAL:
            if not self.last_run:
                return True
            return now - self.last_run >= self.interval_seconds
        if self.schedule_type == ScheduleType.CRON:
            if not self.next_run:
                return True
            return now >= self.next_run
        return False

    def update_next_run(self, now: float) -> None:
        if self.schedule_type == ScheduleType.INTERVAL:
            self.next_run = (self.last_run or now) + self.interval_seconds
        elif self.schedule_type == ScheduleType.CRON:
            if self.cron_expr:
                c = croniter.croniter(self.cron_expr, now)
                self.next_run = c.get_next(float)


class nexus_agent AgentScheduler:
    """Task scheduler for nexus_agent Agent. Runs periodic tasks like health checks, memory cleanup, etc."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_interval_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval_seconds: float,
        metadata: Any = None,
    ) -> None:
        with self._lock:
            task = ScheduledTask(
                id=task_id,
                name=name,
                func=func,
                schedule_type=ScheduleType.INTERVAL,
                interval_seconds=interval_seconds,
                metadata=metadata,
                enabled=True,
            )
            task.last_run = time.time() - interval_seconds  # Run on startup
            task.update_next_run(time.time())
            self._tasks[task_id] = task
            logger.info("scheduled_interval_task_added", task_id=task_id, interval=interval_seconds)

    def add_cron_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        cron_expr: str,
        metadata: Any = None,
    ) -> None:
        with self._lock:
            task = ScheduledTask(
                id=task_id,
                name=name,
                func=func,
                schedule_type=ScheduleType.CRON,
                cron_expr=cron_expr,
                metadata=metadata,
                enabled=True,
            )
            task.update_next_run(time.time())
            self._tasks[task_id] = task
            logger.info("scheduled_cron_task_added", task_id=task_id, cron=cron_expr)

    def add_one_time_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        run_at: float,
        metadata: Any = None,
    ) -> None:
        with self._lock:
            task = ScheduledTask(
                id=task_id,
                name=name,
                func=func,
                schedule_type=ScheduleType.ONCE,
                run_at=run_at,
                metadata=metadata,
                enabled=True,
            )
            self._tasks[task_id] = task
            logger.info("scheduled_one_time_task_added", task_id=task_id, run_at=run_at)

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def enable_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = True
                return True
            return False

    def disable_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].enabled = False
                return True
            return False

    def list_tasks(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "type": t.schedule_type.value,
                    "enabled": t.enabled,
                    "last_run": t.last_run,
                    "next_run": t.next_run,
                    "interval": t.interval_seconds,
                    "cron": t.cron_expr,
                }
                for t in self._tasks.values()
            ]

    def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                tasks_to_run = [
                    (t, now) for t in self._tasks.values() if t.should_run(now)
                ]

            for task, now in tasks_to_run:
                try:
                    task.last_run = now
                    task.update_next_run(now)
                    # Run in a separate thread so scheduler doesn't block
                    t = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
                    t.start()
                except Exception as e:
                    logger.error("scheduler_task_error", task_id=task.id, error=str(e))

            time.sleep(1.0)  # Check every second

    def _execute_task(self, task: ScheduledTask) -> None:
        try:
            task.func()
        except Exception as e:
            logger.error("scheduler_task_execution_error", task_id=task.id, error=str(e))

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("scheduler_started", task_count=len(self._tasks))

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("scheduler_stopped")


# Global scheduler
scheduler = nexus_agent AgentScheduler()