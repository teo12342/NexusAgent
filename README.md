# nexus_agent Agent — Next-Generation AI Agent Platform

**Status:** Building  
**Version:** 0.1.0  
**Built by:** Teo + Jarvis

---

## What is nexus_agent Agent?

nexus_agent Agent is a next-generation AI agent platform built from scratch in Python. It's the platform Teo is building to replace and exceed what OpenClaw can do. Everything runs locally, connects to MiniMax M2.7 and Ollama, and is built for 100% device control.

## Architecture

```
nexus_agent Agent/
├── src/
│   ├── core/         # Event bus, scheduler, config (pydantic validation)
│   ├── device/       # Full Windows API — process, registry, services, power
│   ├── memory/       # Vector store (ChromaDB) + graph (NetworkX)
│   ├── vision/       # Screen capture + Ollama vision models
│   ├── voice/        # TTS/STT (placeholder for ElevenLabs + Whisper)
│   ├── tools/        # 25+ tools — device, memory, vision, web, file
│   ├── agent/        # Agent core — LLM orchestration, tool execution
│   ├── protocol/      # Multi-agent protocol
│   └── dashboard/    # Flask web dashboard
├── data/            # Memory storage, session DB, logs
├── config.yaml       # All configuration
└── requirements.txt  # Python dependencies
```

## Features

- 🧠 **Persistent memory** — vector + graph, auto-learns from corrections
- 🖥️ **Full device control** — process mgmt, registry, services, power
- 👁️ **Native vision** — screenshots to Ollama vision models
- 🔊 **Voice-ready** — ElevenLabs TTS + Whisper STT
- 🎛️ **Real dashboard** — live stats, process list, memory browser, chat, tool executor
- 🛡️ **Self-healing** — watchdog, graceful degradation, error recovery
- 🔗 **25+ tools** — device, memory, vision, web, file — all registered in one registry
- 🤖 **Agent core** — streaming responses, memory context injection, fallback chain

## Install

```bash
cd nexus_agent Agent
pip install -r requirements.txt
python -m src.dashboard.app
```

Dashboard: `http://127.0.0.1:18790`

## Config

Edit `config.yaml` to set:
- API keys (MINIMAX_API_KEY, TELEGRAM_BOT_TOKEN)
- Model preferences
- Dashboard port and password

## Status

Phase 1 (Core) — in progress. Dashboard, device control, memory, tools, agent core done. Voice and multi-agent protocol coming next.

## Why nexus_agent Agent?

Because building it yourself means it does exactly what you need, runs on your machine, and doesn't break when you update ChatGPT.