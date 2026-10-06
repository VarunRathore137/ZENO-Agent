<div align="center">

# ⚡ ZENO 2.0 — Autonomous Multi-Agent Framework & Persistent Context Engine

**Stateful · Locally-Running · Production-Grade Agentic Infrastructure**

A high-throughput AI execution framework with a persistent memory core, async multi-tool dispatch, and real-time bidirectional telemetry — designed for autonomous operation on commodity hardware.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-OS_Agent-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_·_FTS5-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Gemini](https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![Rust](https://img.shields.io/badge/Tauri_2-Rust_Shell-000000?style=for-the-badge&logo=rust&logoColor=white)](https://tauri.app)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 🧠 What is ZENO?

ZENO is a **stateful, locally-running agentic AI framework** built for high-throughput autonomous execution. Rather than relying on stateless LLM API wrappers, ZENO implements a **persistent SQLite FTS5 memory core** to maintain continuous context across sessions, paired with a **FastAPI-driven OS agent** that dispatches complex multi-step reasoning across **90+ specialized tools**.

It features a **dual-mode communication layer** — WebSockets for real-time state telemetry and REST for CRUD operations — and enforces **human-in-the-loop authorization gates** for destructive terminal commands, preventing non-deterministic LLM outputs from causing irreversible system actions.

The voice interface (`"Hey Zeno"`) is the end-user abstraction layer. The underlying system is an **asynchronous, multi-agent dispatch engine** with structured tool-call schemas, fallback routing, and observable state at every layer.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ZENO — Execution Core                       │
│                                                                 │
│  INPUT LAYER              PROCESSING CORE           EXECUTION   │
│                                                                 │
│  Dual-Path Wake      →    NLP Intent Parser    →   OS Agent     │
│  (Acoustic +              (52 intents, 31           (90+ tools,  │
│   WebRTC VAD)              slot types, ≥0.75        FastAPI,     │
│                            confidence gate)         port 8765)   │
│  Gemini Live Audio   →    LLM Router          →   REST API      │
│  (bidirectional           (rule-based first,       (CRUD, mem,  │
│   streaming)               Gemini fallback)         port 8766)   │
│                                 │                               │
│                                 ▼                               │
│                    SQLite WAL (Zeno.db)                         │
│                    22 tables · FTS5 · 4 views                   │
│                    7 triggers · 25+ indexes                     │
│                                 │                               │
│                                 ▼                               │
│             WebSocket Broadcast (port 8767)                     │
│             state events · toasts · browser ext                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tool Dispatch Pipeline
```
Voice / Text Input
  → Dual-path wake detection (acoustic model ∥ WebRTC VAD + Whisper-tiny transcript)
  → Whisper-base STT (offline)
  → NLP intent classifier (confidence ≥ 0.75 → structured dispatch)
  → LLM fallback (Gemini 2.0 Flash, if NLP confidence < threshold)
  → Action Dispatcher → Tool Call (FastAPI OS Agent, port 8765)
  → Structured JSON response → TTS synthesis → WS broadcast → UI state update
  → Async post-turn: Gemini memory extraction → SQLite UPSERT
```

### Port Map
| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| `8765` | OS Agent | HTTP (FastAPI + uvicorn) | 90+ desktop tool calls |
| `8766` | REST API | HTTP (FastAPI) | CRUD — tasks, memory, sessions, sudo confirm |
| `8767` | WS Server | WebSocket | State telemetry, toasts, browser extension |

---

## 🔑 Core Infrastructure

### Persistent AI Memory Engine
**File:** `zeno/ai/memory.py`

Engineered an async data extraction pipeline that analyzes dialogue post-turn and categorizes durable facts into a **7-category taxonomy** stored in WAL-mode SQLite. Memory is retrieved and injected into system prompts at runtime with **sub-millisecond read latency** (indexed `updated_at` column, `LIMIT 100` scan).

- **Extraction:** Gemini structured output (`response_mime_type: application/json`) with a typed transaction schema (`ADD` / `UPDATE` / `REMOVE`)
- **Injection:** Memory "knowledge card" prepended to system prompt on every turn — no repetitive context re-establishment
- **Pruning:** Automatic `ORDER BY updated_at DESC LIMIT 100` — recency-weighted, bounded storage
- **Thread-safety:** `_is_consolidating` guard prevents concurrent extraction races

**7 Categories:** Identity · Preferences · Goals · Projects · Relationships · Emotional · Behavior

```python
# Extraction schema (structured JSON output from Gemini)
{
  "transactions": [
    {"action": "ADD",    "category": "goal",    "text": "Building an AI startup"},
    {"action": "UPDATE", "id": "a3f91",         "text": "Now using FastAPI over Flask"},
    {"action": "REMOVE", "id": "b1c22"}
  ]
}
```

---

### 90+ Tool Agent — FastAPI Dispatch Layer
**Directory:** `zeno/agent/`

A standalone FastAPI server (`uvicorn`, port 8765) that registers tools via `@register` decorators and dispatches calls by name from the Gemini function-calling schema. Cross-platform OS backends (Windows · macOS · Linux · Wayland) are resolved at runtime via a factory pattern.

**Dynamic path resolution** for tools that are not on `PATH` (e.g. Spotify in `%APPDATA%`, Chrome in `Program Files`) — walks `_KNOWN_PATHS` and performs a shallow `os.scandir` across `%LOCALAPPDATA%`, `%APPDATA%`, and `%PROGRAMFILES%` before falling back to shell resolution.

**Safety enforcement:** Terminal tool has a `BLACKLIST` of destructive commands (`rm -rf`, `format c:`, `diskpart`, etc.) and routes elevated commands through a **two-phase tokenized authorization protocol** (SudoPopup modal with 60-second countdown) before execution.

**Tool categories:**
Applications · Browser · Camera · Clipboard · Coding · Files · Google APIs · News · OS Input · Power Control · Screenshot + OCR · Search · System Metrics · Terminal · Weather · Window Management · Websites

---

### Dual-Path Wake Detection
**File:** `zeno/__main__.py`

Two concurrent detection paths run in parallel threads, both writing to a shared `threading.Event`:

| Path | Mechanism | Latency | Reliability |
|------|-----------|---------|-------------|
| **A — Acoustic** | `openWakeWord` ONNX model, 80ms frames | ~instant | High (acoustic signature) |
| **B — Transcript** | `WebRTC VAD` mode 2 + `Whisper-tiny`, 1.5s windows | ~1–3s | Highest (speech + text) |

**WebRTC VAD configuration** (tuned for Intel Smart Sound Array mics with hardware AGC):
- Mode 2 (aggressive noise rejection — higher than default)
- Requires **6 consecutive** 20ms speech frames (~120ms) before passing audio to Whisper
- Resets count on any silence frame (prevents keyboard transients from accumulating)
- RMS fallback gate: `0.003` (10× tighter than naïve implementations)

**Queue architecture:** Single `MicrophoneStream` fan-outs to 3 independent `queue.Queue` consumers — acoustic detector, VAD scanner, command collector — with no frame-stealing race conditions.

---

### Multi-Phase Socratic Reasoning Pipeline
**File:** `zeno/ai/rubber_duck.py`

A **6-state LLM-driven state machine** that guides structured problem decomposition and outputs a complete PRD document with auto-extracted task records inserted directly into SQLite.

```
PROBLEM → CONSTRAINTS → EDGE_CASES → DEPENDENCIES → CRITERIA → GENERATING
```

- Each phase runs a purpose-specific Gemini prompt with structured output validation
- Session state serialized to SQLite (`rubber_duck_sessions` table) — survives daemon restarts
- On `GENERATING`: LLM output parsed for `---TASKS---` delimiter, tasks bulk-inserted into `tasks` table, PRD written to `~/Zeno/projects/<slug>/PRD.md`

---

### Real-Time Bidirectional Communication Layer
**File:** `zeno/monitor/ws_server.py`

`asyncio`-native WebSocket server (port 8767) serving as the single broadcast hub for all runtime state:

- **State telemetry:** `{type: "zeno_state", state: "idle|listening|thinking|speaking"}` — pushed from voice loop and Gemini Live session via `asyncio.run_coroutine_threadsafe()` (thread-safe cross-thread dispatch)
- **Toast notifications:** Reminder events delivered instantly without polling
- **Browser extension sync:** Tab open/close events with domain privacy redaction
- **Sudo authorization:** Elevated command requests queued and rendered in SudoPopup modal

---

## 💾 Database Schema

**`~/Zeno/Zeno.db`** — SQLite WAL mode · 22 tables · FTS5 virtual table · 4 views · 7 triggers · 25+ indexes

| Section | Tables | Purpose |
|---------|--------|---------|
| **Memory** | `memories` | Persistent AI context — 7-category, auto-extracted, sub-ms retrieval |
| Tasks | `tasks`, `task_dependencies`, `task_history` | Full lifecycle + audit trail |
| Projects | `projects` | Registry with status, color, paths |
| Sessions | `sessions`, `session_pending_items` | Daily session state + memory continuity |
| Time Blocks | `time_blocks`, `schedule_reroutings` | Calendar scheduling |
| Reminders | `reminders` | One-time, recurring, contextual |
| Activity | `activity_log`, `browser_sessions`, `context_switches` | 30s passive OS sampling |
| Analytics | `analytics_weekly`, `analytics_daily`, `behaviour_patterns` | Behavioral patterns |
| Workspaces | `workspaces`, `workspace_steps`, `workspace_activations` | Multi-step macro profiles |
| Voice | `voice_interactions`, `conversations` | Full NLP interaction audit |
| Notes | `notes` + FTS5 | Full-text search — indexed across title, content, tags |
| Reasoning | `rubber_duck_sessions` | Serialized state machine checkpoints |
| System | `app_classifications`, `system_events`, `schema_version` | Whitelist, audit, migrations |
| Identity | `user_profile`, `privacy_exclusions` | Config singleton, privacy blocklist |

---

## ⚙️ Dual Voice Mode Architecture

| | Whisper Mode (default) | Gemini Live Mode (`--live`) |
|---|---|---|
| **Command** | `python -m zeno` | `python -m zeno --live` |
| **STT** | OpenAI Whisper (offline, local) | Gemini native audio (streaming) |
| **Wake** | Dual-path: acoustic + VAD transcript | Always-on bidirectional stream |
| **Tool Dispatch** | NLP → Dispatcher → OS Agent | Gemini function calling → OS Agent |
| **Latency** | ~2–3s post-utterance | Near real-time |
| **Privacy** | 100% on-device, no network calls | Audio streams to Google APIs |
| **Reliability** | Fully offline — no dependency on API availability | Requires `GOOGLE_API_KEY` |

```bash
python -m zeno          # Offline Whisper mode (default)
python -m zeno --live   # Gemini Live bidirectional streaming
```

---

## 🛠️ Technology Stack

### Backend (Python 3.11+)
| Package | Role |
|---------|------|
| `google-genai` | Gemini 2.0 Flash — tool routing, memory extraction, Live audio streaming |
| `openai-whisper` | Local offline STT (base model, 16kHz, float32) |
| `openwakeword` | ONNX acoustic wake word model |
| `webrtcvad` | Voice activity detection (mode 2, consecutive-frame gating) |
| `fastapi` + `uvicorn` | OS Agent (port 8765) + REST API (port 8766) |
| `websockets` | Async WS server (port 8767) — state, toasts, browser events |
| `apscheduler` | Persistent job scheduler — reminders, briefings |
| `pyttsx3` | Offline TTS (dedicated COM thread on Windows to avoid CoInitialize races) |
| `sounddevice` | Low-latency mic capture with queue fan-out |
| `rapidfuzz` | Fuzzy wake phrase matching (threshold ≥ 85, consecutive-word gating) |
| `psutil` | System metrics (CPU, RAM, disk, GPU) |
| `pygetwindow` + `pywin32` | Window management (Windows backend) |

### Frontend (React 19 + Tauri 2)
| Package | Role |
|---------|------|
| `@tauri-apps/api` | IPC, system tray, autostart registry entry |
| `react` + `vite` | HUD framework + build pipeline |
| `recharts` | Analytics visualization |
| `lucide-react` | Icon system (Memory Dashboard, SudoPopup) |
| WebSocket (`useDaemonWs`) | Real-time state binding to port 8767 |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Rust + Cargo (Tauri shell)
- Node.js 18+ (frontend)
- Google Gemini API key — [ai.google.dev](https://ai.google.dev) (free tier)

### Setup

```bash
git clone https://github.com/VarunRathore137/ZENO-Agent.git
cd ZENO-Agent

# Python environment
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Configure
$env:GOOGLE_API_KEY = "your-gemini-key"   # PowerShell

# Initialize DB (22 tables, FTS5, triggers, indexes)
python scripts/init_db.py

# Run
python -m zeno          # Offline Whisper pipeline
python -m zeno --live   # Gemini Live streaming
```

### Environment Variables
| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_API_KEY` | ✅ | Gemini — memory extraction, LLM fallback, Live mode |
| `ZENO_VOICE_MODE` | Optional | `"live"` to default to streaming mode |
| `ZENO_DEBUG` | Optional | `"1"` for verbose structured logging |
| `ZENO_AGENT_PORT` | Optional | Override OS Agent port (default: `8765`) |
| `ELEVENLABS_API_KEY` | Optional | Premium TTS provider |

---

## 🧩 NLP Intent System

**52 named intents · 10 categories · 31 slot types**

| Category | Intents |
|----------|---------|
| Task Management | `add_task`, `update_task`, `complete_task`, `list_tasks`, `flag_blocker` |
| Session Control | `start_session`, `end_session`, `resume_session`, `deliver_briefing` |
| Scheduling | `add_time_block`, `rebalance_schedule`, `query_schedule` |
| Reminders | `add_reminder`, `snooze_reminder`, `list_reminders` |
| Workspace Macros | `activate_workspace`, `save_workspace`, `enable_focus_mode` |
| Analytics | `query_focus_time`, `query_distraction_report`, `query_weekly_summary` |
| **Reasoning Pipeline** | `start_rubber_duck`, `generate_prd` |
| Notes | `add_note`, `search_notes`, `read_note` |
| OS Control | `open_app`, `close_app`, `set_volume`, `screenshot`, `read_screen` |
| System | `initiate_shutdown`, `toggle_dnd`, `check_status` |

**Multi-turn state machines:**
| Flow | States |
|------|--------|
| Socratic Reasoning | `PROBLEM → CONSTRAINTS → EDGE_CASES → DEPS → CRITERIA → GENERATING` |
| Day Planning | `LOADING → PRESENTING → BLOCKING → CONFIRMING → DONE` |
| Shutdown Ritual | `CAPTURING → PROMPTING → SAVING → DONE` |
| Schedule Re-routing | `ANALYSING → PROPOSING → AWAITING → APPLYING` |

---

## 🔒 Safety & Security Architecture

| Control | Implementation |
|---------|---------------|
| **Human-in-the-loop authorization** | Two-phase tokenized SudoPopup (60s countdown) for elevated terminal commands |
| **Destructive command blacklist** | `rm -rf /`, `format c:`, `diskpart`, `del /f /s /q` and others blocked at tool layer |
| **Privacy redaction** | Window titles and browser domains redacted against `privacy_exclusions` before any DB write |
| **Offline-first default** | Whisper mode makes zero network calls — full functionality with no internet |
| **API key isolation** | Keys from environment only — never persisted to config files or DB |
| **App execution whitelist** | Macro engine resolves only registered app specs — no arbitrary shell execution |

---

## 📁 Project Structure

```
ZENO-Agent/
├── zeno/
│   ├── __main__.py          # Daemon entry: dual-path wake, TTS thread, WS broadcast
│   ├── ai/
│   │   ├── memory.py        # Persistent memory engine — async extraction, prompt injection
│   │   ├── providers.py     # LLM provider router (Gemini / Claude)
│   │   ├── briefing.py      # Context-aware morning briefing generator
│   │   ├── rubber_duck.py   # 6-state Socratic reasoning state machine
│   │   ├── prd_writer.py    # PRD generation + task auto-extraction
│   │   └── prompts.py       # YAML prompt loader
│   ├── agent/
│   │   ├── server.py        # FastAPI tool server (port 8765)
│   │   ├── dispatch.py      # Tool call dispatcher
│   │   ├── registry.py      # @register decorator tool registry
│   │   ├── backends/        # OS backends (Windows · macOS · Linux · Wayland)
│   │   └── tools/           # 90+ tool implementations
│   ├── api/                 # FastAPI REST (port 8766) — memories, tasks, sessions, sudo
│   ├── dispatcher/          # Intent → handler routing
│   ├── handlers/            # Domain handlers: tasks, notes, reminders, sessions
│   ├── monitor/
│   │   ├── ws_server.py     # Async WebSocket broadcast hub (port 8767)
│   │   ├── activity.py      # 30s passive OS sampling
│   │   └── privacy.py       # Window title / domain redaction
│   ├── nlp/                 # Intent classifier + slot extractor
│   ├── scheduler/           # APScheduler job manager
│   ├── tts/                 # TTS engine adapters
│   └── voice/
│       ├── capture.py       # Mic fan-out queue architecture
│       ├── wake_word.py     # Acoustic + fuzzy transcript wake detection
│       ├── transcriber.py   # Whisper STT wrapper
│       ├── hotkeys.py       # Global hotkeys (Ctrl+Shift+Space, Ctrl+Shift+J)
│       └── gemini_live.py   # Gemini Live bidirectional streaming session
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ArcReactor.tsx          # State visualizer (idle · listening · thinking · speaking)
│       │   ├── CharacterVisualizer.tsx # State-synced video overlay
│       │   ├── MemoryDashboard.tsx     # Memory browser — inspect, add, delete
│       │   ├── SudoPopup.tsx           # Elevated command authorization modal
│       │   ├── Toast.tsx               # Real-time WS-delivered notifications
│       │   ├── Dashboard.tsx           # Analytics HUD
│       │   └── Settings.tsx            # Configuration panel
│       └── hooks/
│           ├── useDaemonWs.ts          # WebSocket state binding (port 8767)
│           └── useApi.ts               # REST API hook (port 8766)
├── src-tauri/               # Rust Tauri shell — system tray, autostart, WS listener
├── scripts/                 # Init scripts (DB bootstrap, config generation)
├── zeno_usage_guide.md      # Full command reference
├── ZENO_Testing_Cheatsheet.md
├── requirements.txt
└── ARCHITECTURE.md
```

---

## 🤝 Contributing

1. Fork the repo and create a feature branch: `git checkout -b feat/your-feature`
2. Commit: `git commit -m "feat: your feature"`
3. Push and open a PR

Code style: **Black + Ruff** for Python · **TypeScript strict mode** for frontend.

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

<div align="center">

**Built by [Varun Rathore](https://github.com/VarunRathore137)**

*Production-grade agentic infrastructure. Personal assistant is just the interface.*

</div>
