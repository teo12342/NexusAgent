"""
nexus_agent Agent — src/agent/nexus_agent Agent_agent.py
Main agent that connects LLM, memory, tools, and vision
"""

import time
import json
import structlog
import threading
import queue
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..memory import MemoryManager
from ..device import DeviceSystem
from ..vision import ScreenCapture, ScreenAnalyzer
from ..core.event_loop import event_bus, Event, EventType
from ..core.config import get_config

logger = structlog.get_logger()


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Dict]] = None
    timestamp: float = field(default_factory=time.time)


class nexus_agent AgentAgent:
    """
    Main agent — orchestrates LLM + memory + tools.
    Handles streaming, tool calling, context management, fallback.
    """

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ):
        self.config = get_config()
        self.memory = memory or MemoryManager()
        self.device = DeviceSystem()
        self.screen = ScreenCapture()
        self.analyzer = ScreenAnalyzer()
        self.on_token = on_token  # Streaming callback

        self._sessions: Dict[str, List[Message]] = {}
        self._running = False
        self._model_client = None
        self._connect_model()

    def _connect_model(self) -> None:
        """Connect to the primary LLM (MiniMax)."""
        try:
            import anthropic
            api_key = self.config.get_model_api_key(
                self.config.models.primary if self.config.models else None
            )
            if api_key:
                self._model_client = anthropic.Anthropic(api_key=api_key)
                logger.info("agent_connected_to_minimax")
            else:
                logger.warning("no_api_key_for_agent")
        except ImportError:
            logger.warning("anthropic_not_installed")

    def create_session(self, session_id: str, system_prompt: str = "") -> None:
        """Start a new agent session."""
        messages = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        self._sessions[session_id] = messages
        event_bus.emit(Event(EventType.SESSION_NEW, {"session_id": session_id}))

    def send_message(
        self,
        session_id: str,
        user_message: str,
        stream: bool = True,
    ) -> str:
        """
        Send a message to the agent and get a response.
        If stream=True, tokens are sent via on_token callback.
        Returns the full response string.
        """
        if session_id not in self._sessions:
            self.create_session(session_id)

        # Add user message
        self._sessions[session_id].append(Message(role="user", content=user_message))

        # Inject memory context
        context = self.memory.recall(user_message, limit=5)
        memory_context = self._format_memory_context(context)
        if memory_context:
            self._sessions[session_id].append(
                Message(role="system", content=f"[Relevant Memory]\n{memory_context}")
            )

        # Build API messages
        api_messages = self._build_api_messages(session_id)

        # Get response
        response_text = ""
        try:
            if self._model_client and stream and self.on_token:
                response_text = self._stream_response(api_messages)
            elif self._model_client:
                response_text = self._blocking_response(api_messages)
            else:
                response_text = "[No LLM connected — configure MiniMax API key]"
        except Exception as e:
            logger.error("agent_response_error", error=str(e))
            response_text = f"[Error: {str(e)}]"

        # Add assistant response
        self._sessions[session_id].append(Message(role="assistant", content=response_text))

        # Learn from the exchange
        self.memory.add_session_message("user", user_message, session_id)
        self.memory.add_session_message("assistant", response_text, session_id)

        return response_text

    def _format_memory_context(self, context: Dict) -> str:
        parts = []
        for r in context.get("vector_results", []):
            parts.append(f"- {r['content']}")
        if parts:
            return "\n".join(parts[:5])
        return ""

    def _build_api_messages(self, session_id: str) -> List[Dict]:
        msgs = []
        for msg in self._sessions[session_id]:
            m = {"role": msg.role, "content": msg.content}
            msgs.append(m)
        return msgs

    def _blocking_response(self, messages: List[Dict]) -> str:
        model_name = self.config.models.primary.model if self.config.models else "MiniMax-M2.7"
        resp = self._model_client.messages.create(
            model=model_name,
            max_tokens=self.config.models.primary.max_tokens if self.config.models else 131072,
            messages=messages,
        )
        return resp.content[0].text if resp.content else ""

    def _stream_response(self, messages: List[Dict]) -> str:
        model_name = self.config.models.primary.model if self.config.models else "MiniMax-M2.7"
        full_response = []

        with self._model_client.messages.stream(
            model=model_name,
            max_tokens=self.config.models.primary.max_tokens if self.config.models else 131072,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response.append(text)
                if self.on_token:
                    self.on_token(text)

        return "".join(full_response)

    def execute_tool(self, tool_name: str, tool_args: Dict) -> Dict:
        """Execute a named tool with the given arguments."""
        from ..tools import TOOL_REGISTRY

        if tool_name not in TOOL_REGISTRY:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            tool_func = TOOL_REGISTRY[tool_name]
            result = tool_func(**tool_args)
            return result
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return {"error": str(e)}

    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get message history for a session."""
        if session_id not in self._sessions:
            return []
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in self._sessions[session_id]
        ]

    def get_all_stats(self) -> Dict:
        return {
            "active_sessions": len(self._sessions),
            "memory_stats": self.memory.get_stats(),
            "system_stats": self.device.get_full_stats(),
        }


# Default agent instance
default_agent: Optional[nexus_agent AgentAgent] = None


def get_agent() -> nexus_agent AgentAgent:
    global default_agent
    if default_agent is None:
        default_agent = nexus_agent AgentAgent()
    return default_agent