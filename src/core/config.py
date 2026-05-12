"""
Nexus Agent — src/core/config.py
Loads and validates config.yaml
"""

import os
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


def load_config(config_path: str = None) -> "NexusAgentConfig":
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config.yaml"
        )

    cfg = NexusAgentConfig()
    if os.path.exists(config_path):
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return NexusAgentConfig(**data)
    return cfg


def get_config() -> "NexusAgentConfig":
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


class ModelConfig(BaseModel):
    provider: str = "minimax"
    model: str = "MiniMax-M2.7"
    max_tokens: int = 131072
    temperature: float = 0.7
    api_key: Optional[str] = None


class ModelsConfig(BaseModel):
    primary: ModelConfig = ModelConfig()
    fallback: Optional[ModelConfig] = None


class MemoryConfig(BaseModel):
    vector_db_path: str = "data/memory/vector_db"
    graph_db_path: str = "data/memory/graph_db"
    auto_learn: bool = True
    max_entries: int = 10000


class DeviceConfig(BaseModel):
    check_interval_ms: int = 5000
    enable_registry: bool = True
    enable_services: bool = True


class VisionConfig(BaseModel):
    capture_backend: str = "mss"
    default_model: Optional[str] = None
    screenshot_path: str = "data/screenshots"


class VoiceConfig(BaseModel):
    tts_provider: str = "elevenlabs"
    stt_provider: str = "whisper"
    api_key: Optional[str] = None


class DashboardConfig(BaseModel):
    port: int = 18790
    host: str = "127.0.0.1"
    password: Optional[str] = None


class WatchdogConfig(BaseModel):
    enabled: bool = True
    check_interval_ms: int = 30000
    auto_restart: bool = True


class NexusAgentConfig(BaseModel):
    name: str = "Nexus Agent"
    version: str = "0.1.0"
    models: ModelsConfig = ModelsConfig()
    memory: MemoryConfig = MemoryConfig()
    device: DeviceConfig = DeviceConfig()
    vision: VisionConfig = VisionConfig()
    voice: VoiceConfig = VoiceConfig()
    dashboard: DashboardConfig = DashboardConfig()
    watchdog: WatchdogConfig = WatchdogConfig()

    def get_model_api_key(self, model_name: str = None) -> Optional[str]:
        if self.models.primary and self.models.primary.api_key:
            return self.models.primary.api_key
        return os.environ.get("MINIMAX_API_KEY")


_config: Optional[NexusAgentConfig] = None