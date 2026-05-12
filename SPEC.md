# nexus_agent Agent — Next-Generation AI Agent Platform

**Version:** 0.1.0  
**Status:** In Development  
**Last Updated:** 2026-05-12

---

## Vision

nexus_agent Agent is an AI agent platform that puts everything we know about AI agents into one unified system. Built for Teo, powered by Teo. Not a clone of OpenClaw or any existing platform — a ground-up rethinking of what an AI agent should be.

The name says it all: every component connects to every other. Memory feeds context, context feeds reasoning, reasoning triggers tools, tools report back, memory updates. Everything is connected.

**Core philosophy:**
- It just works
- Full device control — no sandbox, no limitations
- Memory that actually remembers
- Vision and voice as first-class citizens
- A dashboard that shows you everything
- Doesn't break — self-heals, recovers, never leaves you hanging

---

## Architecture Overview

```
nexus_agent Agent
├── src/
│   ├── core/            # Main loop, event bus, scheduler, config
│   ├── agent/           # LLM orchestration, reasoning, tool use
│   ├── device/          # Windows API access, process mgmt, registry
│   ├── memory/          # Vector store, graph store, auto-learner
│   ├── vision/          # Screenshot, screen analysis, click detection
│   ├── voice/           # TTS, STT, voice I/O
│   ├── tools/           # All tool definitions and tool chains
│   ├── protocol/        # Multi-agent protocol, inter-agent messaging
│   └── dashboard/       # Web dashboard (Flask + static)
├── data/
│   ├── memory/          # Vector embeddings, graph DB
│   ├── sessions/        # Session history database (SQLite)
│   └── logs/            # Structured logs
├── cache/              # Temp files, model cache
└── logs/               # Application logs
```

---

## Core Features

### 🤖 Agent Core
- **LLM orchestration** — connects to MiniMax (primary) + Ollama (local) + any OpenAI-compatible API
- **Intelligent tool use** — agent decides which tools to call, chains them automatically
- **Context management** — rolling context window with priority weighting (recent > important > recurring)
- **Fallback chain** — if primary model fails, gracefully falls through to backup models
- **Streaming responses** — real-time token output to Telegram/dashboard
- **Multi-turn reasoning** — thinks through complex tasks step by step

### 🧠 Memory System
Two-tier architecture:
1. **Vector store** (ChromaDB) — semantic search across all conversations, files, knowledge
2. **Graph store** (NetworkX) — relationships between concepts, people, projects, preferences
3. **Auto-learner** — learns from corrections, feedback, repeated patterns
4. **Forgetting** — ages out low-value memories to keep vector DB fast and relevant
5. **Recall** — retrieves relevant context before each LLM call, injects seamlessly

### 🖥️ Device Control (Windows API)
Full Windows access via Python Win32 API:
- **Process management** — list, start, stop, kill, priority, CPU/memory usage per process
- **Registry** — read/write/delete registry keys (HKLM, HKCU, HKU)
- **Services** — list, start, stop, restart Windows services
- **Startup items** — add/remove from Windows startup
- **Power** — shutdown, restart, sleep, lock, restart applications
- **Files** — full filesystem access with metadata
- **System info** — CPU, RAM, disk, network, battery, temperature
- **Window management** — enumerate windows, move, resize, minimize, maximize
- **Registry autostart** — set up nexus_agent Agent as a Windows service that starts with the PC

### 👁️ Vision (Native)
- **Screenshot capture** — full screen, window, region — numpy array to vision model
- **Screen understanding** — describes what's on screen, identifies UI elements
- **Click detection** — finds clickable coordinates for any element described
- **Image embedding** — screenshots embedded into memory for later retrieval
- **Vision models** — Ollama (llava, qwen2-vl, moondream2) — fully offline
- **Screen diff** — detect when something on screen changes

### 🔊 Voice (First-Class)
- **STT** — speech to text via Ollama Whisper (local, offline)
- **TTS** — text to speech via ElevenLabs (configurable voice)
- **Voice mode** — full conversation in voice, natural back-and-forth
- **Audio messages** — Telegram voice messages transcribed and processed

### 🔗 Tool System
**Tool categories:**
1. **Device tools** — process, registry, services, power, filesystem
2. **Memory tools** — search, recall, learn, forget, facts
3. **Vision tools** — capture, analyze, click, diff
4. **Web tools** — search, fetch, scrape
5. **Communication tools** — Telegram, email (future)
6. **Code tools** — run Python, run Lua, run shell
7. **File tools** — read, write, edit, explore
8. **Agent tools** — delegate to sub-agent, coordinate multi-agent

**Tool chaining:**
- Agent outputs a JSON plan, nexus_agent Agent executes step by step
- Output of each tool feeds into the next automatically
- Conditional branching — "if X, do Y, else do Z"
- Retry logic with exponential backoff
- Full error recovery mid-chain

### 🎛️ Dashboard (Web UI)
**Sections:**
1. **Home** — system status, recent activity, quick actions
2. **Sessions** — visual session browser, search, playback
3. **Memory** — graph explorer, vector search, memory editor
4. **Files** — file browser with drag-and-drop upload
5. **System** — live CPU/RAM/disk/network, process list
6. **Tools** — tool output logs, chain visualization
7. **Settings** — model config, API keys, voice settings

**Tech:** Flask backend + vanilla JS frontend (no framework needed)

### 🛡️ Reliability
- **Watchdog service** — monitors nexus_agent Agent, auto-restarts crashed components
- **Session checkpointing** — state saved every 30 seconds, recoverable crash
- **Health checks** — every component reports health, failure = alert
- **Error reporting** — clear, actionable error messages not cryptic stack traces
- **Graceful degradation** — if vision fails, fall back to description; if local fails, use cloud

### 👥 Multi-Agent Protocol
- **Sub-agents** — spawn isolated agents for parallel tasks
- **Delegation** — agent can hand off a task to a specific sub-agent
- **Shared memory** — sub-agents can access shared context
- **Inter-agent messaging** — agents can send messages to each other
- **Coordinator pattern** — one master agent coordinates multiple specialist agents

### 📊 Session History
- **SQLite database** — all sessions stored with full message history
- **Search** — full-text search across all sessions
- **Playback** — replay any past session
- **Export** — export session as JSON/Markdown
- **Tags** — tag sessions for organization (project, date, type)

---

## Tech Stack

- **Language:** Python 3.12+
- **LLM:** MiniMax M2.7 (primary), Ollama (local models)
- **Vector DB:** ChromaDB
- **Graph DB:** NetworkX (simple, no server needed)
- **Web framework:** Flask (lightweight)
- **Windows API:** pywin32, psutil, wmi
- **Vision:** OpenCV + Ollama vision models
- **Voice:** ElevenLabs SDK, FasterWhisper
- **HTTP:** requests, aiohttp
- **Database:** SQLite (sessions), JSON (config)
- **Telegram:** python-telegram-bot
- **Async:** asyncio, threading
- **Logging:** structlog

---

## API Design

### Core REST endpoints
```
GET  /api/health              — system health
GET  /api/sessions            — list sessions
GET  /api/sessions/{id}       — get session messages
POST /api/sessions            — create new session
GET  /api/memory/search       — search memory
GET  /api/memory/graph        — get memory graph
POST /api/memory              — add memory
GET  /api/system/stats        — live system stats
GET  /api/system/processes    — process list
POST /api/tools/execute       — execute a tool
GET  /api/tools/chains        — list tool chains
POST /api/tools/chains        — create tool chain
```

### WebSocket
```
/ws/agent                     — real-time agent streaming
/ws/system                    — live system stats feed
```

---

## Configuration (config.yaml)
```yaml
nexus_agent Agent:
  name: "nexus_agent Agent"
  owner: "Teo"
  log_level: "INFO"

models:
  primary:
    provider: "minimax"
    model: "MiniMax-M2.7"
    api_key_env: "MINIMAX_API_KEY"
  local:
    provider: "ollama"
    base_url: "http://127.0.0.1:11434/v1"

memory:
  vector_db: "chroma"
  persist_dir: "data/memory"
  embedding_model: "nomic-embed-text"
  max_memories: 10000
  forget_threshold: 0.1

device:
  check_interval: 5  # seconds
  log_processes: true
  watch_startup: true

voice:
  stt_provider: "faster_whisper"
  stt_model: "base"
  tts_provider: "elevenlabs"
  tts_voice: "..."  # voice ID

telegram:
  enabled: true
  bot_token_env: "TELEGRAM_BOT_TOKEN"
  owner_id: 8788969906

dashboard:
  port: 18790
  password: "nexus_agent Agent"  # change in production

watchdog:
  enabled: true
  check_interval: 30
  restart_on_crash: true
```

---

## Roadmap

### Phase 1 — Core (current)
- [x] Project structure
- [ ] Core event loop and scheduler
- [ ] Device control module (Windows API)
- [ ] Basic memory system (file-based)
- [ ] Agent core with tool execution
- [ ] Telegram integration
- [ ] Basic dashboard

### Phase 2 — Intelligence
- [ ] ChromaDB vector store integration
- [ ] Graph memory (NetworkX)
- [ ] Auto-learner from corrections
- [ ] Intelligent tool chaining
- [ ] Session playback

### Phase 3 — Perception
- [ ] Native vision (OpenCV + Ollama)
- [ ] Screen capture and analysis
- [ ] Click detection and automation
- [ ] Whisper STT integration
- [ ] ElevenLabs TTS integration
- [ ] Voice mode

### Phase 4 — Reliability
- [ ] Watchdog service
- [ ] Session checkpointing
- [ ] Health checks
- [ ] Graceful degradation
- [ ] Startup as Windows service

### Phase 5 — Multi-Agent
- [ ] Sub-agent spawning
- [ ] Inter-agent protocol
- [ ] Delegation system
- [ ] Coordinator pattern

---

## Why nexus_agent Agent?

**vs OpenClaw:** nexus_agent Agent has everything OpenClaw has, plus native vision/voice, real dashboard, intelligent memory, device API, tool chaining, and self-healing. OpenClaw is a platform we extend. nexus_agent Agent replaces it entirely.

**vs LangChain:** LangChain is for developers building LLM apps. nexus_agent Agent is for Teo using an AI agent daily. One is a framework, the other is a product.

**vs Apple Intelligence / Copilot:** Those are corporate products with corporate limitations. nexus_agent Agent is built for Teo, runs on Teo's machine, and does exactly what Teo needs.