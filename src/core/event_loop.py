"""
nexus_agent Agent Event Loop — src/core/event_loop.py
Main event bus and core loop for nexus_agent Agent
"""

import asyncio
import threading
import time
import structlog
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = structlog.get_logger()


class EventType(Enum):
    # Core
    CORE_START = "core.start"
    CORE_STOP = "core.stop"
    CORE_TICK = "core.tick"
    CORE_ERROR = "core.error"
    # Agent
    AGENT_MESSAGE = "agent.message"
    AGENT_TOOL_CALL = "agent.tool_call"
    AGENT_TOOL_RESULT = "agent.tool_result"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"
    # Device
    DEVICE_STATS = "device.stats"
    DEVICE_PROCESS_CHANGE = "device.process_change"
    DEVICE_SERVICE_CHANGE = "device.service_change"
    # Memory
    MEMORY_ADD = "memory.add"
    MEMORY_SEARCH = "memory.search"
    MEMORY_FORGET = "memory.forget"
    MEMORY_LEARN = "memory.learn"
    # Vision
    VISION_CAPTURE = "vision.capture"
    VISION_ANALYZE = "vision.analyze"
    VISION_CLICK = "vision.click"
    # Voice
    VOICE_STT = "voice.stt"
    VOICE_TTS = "voice.tts"
    VOICE_START = "voice.start"
    VOICE_STOP = "voice.stop"
    # Session
    SESSION_NEW = "session.new"
    SESSION_MESSAGE = "session.message"
    SESSION_END = "session.end"
    # Telegram
    TELEGRAM_UPDATE = "telegram.update"
    TELEGRAM_MESSAGE = "telegram.message"
    # Dashboard
    DASHBOARD_CONNECT = "dashboard.connect"
    DASHBOARD_DISCONNECT = "dashboard.disconnect"
    DASHBOARD_REQUEST = "dashboard.request"


@dataclass
class Event:
    type: EventType
    data: Any = None
    source: str = "nexus_agent Agent"
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None


class EventBus:
    """Central event bus for nexus_agent Agent. All components communicate via events."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.RLock()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "events_processed": 0,
            "events_failed": 0,
            "uptime_seconds": 0,
            "last_event": None,
        }
        self._start_time = time.time()

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    h for h in self._subscribers[event_type] if h != handler
                ]

    def emit(self, event: Event) -> None:
        """Emit an event synchronously (called from any thread)."""
        with self._lock:
            handlers = list(self._subscribers.get(event.type, []))
            self._stats["events_processed"] += 1
            self._stats["last_event"] = event.type.value

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self._stats["events_failed"] += 1
                logger.error("event_handler_error", event=event.type.value, handler=handler.__name__, error=str(e))

    async def emit_async(self, event: Event) -> None:
        """Emit an event asynchronously."""
        await self._event_queue.put(event)

    def _async_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Background async loop for processing queued events."""
        asyncio.set_event_loop(loop)
        while self._running:
            try:
                event = asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                with self._lock:
                    handlers = list(self._subscribers.get(event.type, []))
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            asyncio.create_task(handler(event))
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error("async_event_handler_error", event=event.type.value, error=str(e))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("async_loop_error", error=str(e))

    def start(self) -> None:
        """Start the event bus."""
        if self._running:
            return
        self._running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._async_loop, args=(self._loop,), daemon=True)
        self._thread.start()
        logger.info("event_bus_started")

    def stop(self) -> None:
        """Stop the event bus."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("event_bus_stopped", stats=self._stats)

    def get_stats(self) -> Dict:
        self._stats["uptime_seconds"] = int(time.time() - self._start_time)
        return dict(self._stats)


# Global event bus instance
event_bus = EventBus()