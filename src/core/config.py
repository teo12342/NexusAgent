"""
nexus_agent Agent Config — src/core/config.py
Loads and validates config.yaml
"""

import os
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class ModelConfig(BaseModel):
    provider: str
    model: str
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 131072
    context_window: int = 204800


class ModelsConfig(BaseModel):
    primary: ModelConfig
    local: Optional[ModelConfig] = None
    fallback_order: List[str] = Field(default_factory=list)


class MemoryConfig(BaseModel):
    vector_db: str = "chroma"
    persist_dir: str = "data/memory"
    embedding_model: str = "nomic-embed-text"
    max_memories: int = 10000
    forget_threshold: float = 0.1
    session_context_lines: int = 50


class DeviceConfig(BaseModel):
    check_interval: int = 5
    log_processes: bool = True
    watch_startup: bool = True


class VisionConfig(BaseModel):
    capture_method: str = "pillow"
    default_region: str = "fullscreen"
    click_detection: bool = True


class VoiceConfig(BaseModel):
    stt_provider: str = "faster_whisper"
    stt_model: str = "base"
    tts_provider: str = "elevenlabs"
    tts_voice: str = ""
    audio_format: str = "mp3"


class TelegramConfig(BaseModel):
    enabled: bool = True
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    owner_id: int = 0
    streaming: bool = True


class DashboardConfig(BaseModel):
    port: int = 18790
    host: str = "127.0.0.1"
    password: str = "nexus_agent Agent"
    ssl: bool = False


class WatchdogConfig(BaseModel):
    enabled: bool = True
    check_interval: int = 30
    restart_on_crash: bool = True
    max_restart_attempts: int = 3


class ToolsConfig(BaseModel):
    timeout_default: int = 30
    timeout_max: int = 300
    retry_attempts: int = 2
    retry_delay: int = 2


class nexus_agent AgentConfig(BaseModel):
    nexus_agent Agent: Dict = Field(default_factory=lambda: {"name": "nexus_agent Agent", "owner": "Teo", "log_level": "INFO", "version": "0.1.0"})
    models: Optional[ModelsConfig] = None
    memory: Optional[MemoryConfig] = None
    device: Optional[DeviceConfig] = None
    vision: Optional[VisionConfig] = None
    voice: Optional[VoiceConfig] = None
    telegram: Optional[TelegramConfig] = None
    dashboard: Optional[DashboardConfig] = None
    watchdog: Optional[WatchdogConfig] = None
    tools: Optional[ToolsConfig] = None

    def get_model_api_key(self, model_cfg: ModelConfig) -> str:
        if model_cfg.api_key_env:
            return os.environ.get(model_cfg.api_key_env, "")
        return ""


_global_config: Optional[nexus_agent AgentConfig] = None


def load_config(config_path: str = "config.yaml") -> nexus_agent AgentConfig:
    global _global_config
    if _global_config is not None:
        return _global_config

    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(p, "r") as f:
        raw = yaml.safe_load(f)

    # Parse subsections with pydantic
    data = raw or {}
    config = nexus_agent AgentConfig(
        nexus_agent Agent=data.get("nexus_agent Agent", {"name": "nexus_agent Agent", "owner": "Teo"}),
        models=ModelsConfig(**data["models"]) if "models" in data else None,
        memory=MemoryConfig(**data["memory"]) if "memory" in data else None,
        device=DeviceConfig(**data["device"]) if "device" in data else None,
        vision=VisionConfig(**data["vision"]) if "vision" in data else None,
        voice=VoiceConfig(**data["voice"]) if "voice" in data else None,
        telegram=TelegramConfig(**data["telegram"]) if "telegram" in data else None,
        dashboard=DashboardConfig(**data["dashboard"]) if "dashboard" in data else None,
        watchdog=WatchdogConfig(**data["watchdog"]) if "watchdog" in data else None,
        tools=ToolsConfig(**data["tools"]) if "tools" in data else None,
    )
    _global_config = config
    return config


def get_config() -> nexus_agent AgentConfig:
    if _global_config is None:
        return load_config()
    return _global_config