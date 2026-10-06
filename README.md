<div align="center">

# ⚡ ZENO 2.0 — Your Personal AI Assistant

<img width="2200" height="1006" alt="ZENO" src="https://github.com/user-attachments/assets/e0c37f02-b438-45e5-a48d-b2b62719fe16" />

**Voice-first. Memory-driven. Locally-running.**

A developer-grade AI personal assistant that listens, thinks, remembers, and acts — all on your machine.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Rust](https://img.shields.io/badge/Rust-Tauri_2-000000?style=for-the-badge&logo=rust&logoColor=white)](https://tauri.app)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![SQLite](https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Gemini](https://img.shields.io/badge/Google-Gemini_2.0-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 🧠 What is ZENO?

ZENO (**Z**ero-overhead **E**xecution & **N**atural **O**rchestration) is a **voice-first, locally-running personal AI assistant** built for developers and knowledge workers.

Say `"Hey Zeno"` — ZENO wakes up, transcribes your speech, classifies your intent, and dispatches the action. Whether that's launching Spotify, adding a task, starting a deep work session, or generating a full PRD — it just works.

ZENO 2.0 adds a **persistent AI memory engine**, **Gemini Live real-time streaming**, a complete **90+ tool OS agent**, and a polished **sci-fi HUD** with a character visualizer, memory dashboard, and secure command authorization.

> **All your data stays on your machine.** External calls are limited to Google Gemini (reasoning + live voice) and optionally ElevenLabs (TTS).

---

## ✨ What's New in ZENO 2.0

### 🧠 Persistent AI Memory Engine
ZENO now **remembers you across every session** — automatically. After each conversation turn, Gemini analyzes the dialogue and extracts durable facts stored in SQLite. Memory is injected naturally into every system prompt — no robotic "According to my records..." — just a conversation with someone who knows you.

**7 memory categories:** Identity · Preferences · Goals · Projects · Relationships · Emotional · Behavior

### 🎙️ Gemini Live — Real-Time Voice Streaming
A brand-new voice mode using Google's bidirectional audio streaming API. Near-instant responses, always-on listening, no wake word required.

```bash
python -m zeno --live    # Gemini Live mode
python -m zeno           # Whisper mode (offline, private — default)
```

### 🛠️ 90+ OS Automation Tools
A complete tool agent with dispatchers for every major OS action:
- **App control** — Spotify, Discord, Chrome, VS Code, Steam, VLC, Zoom, Slack, and more
- **Browser automation** — open URLs, search YouTube, navigate to sites
- **System control** — volume, brightness, screenshots, OCR screen reading
- **File operations** — create, read, search, safe-delete
- **Clipboard, window management, OS input simulation**
- **Terminal execution** — with a safety blacklist for destructive commands

### 🎭 Character Visualizer
Swap the ArcReactor for an animated character overlay synced to ZENO's voice state. Drop your own `idle.mp4`, `thinking.mp4`, `talking.mp4` clips into `frontend/public/assets/` and the overlay comes alive.

### 💾 Memory Dashboard
A full UI panel to inspect, add, and delete what ZENO remembers about you — with category filters, timestamps, and direct SQLite CRUD via the REST API.

### 🔒 SudoPopup — Elevated Command Authorization
Dangerous terminal commands require a two-phase UI confirmation with a 60-second countdown timer before execution. No more accidental destructive operations.

### 🔔 Reminder Toast Notifications
Real-time reminder toasts pushed directly to the HUD via WebSocket — no polling, instant delivery.

---

## ✨ Core Features

### 🎙️ Voice Pipeline

| Feature | Whisper Mode (default) | Live Mode (`--live`) |
|---|---|---|
| **Start** | `python -m zeno` | `python -m zeno --live` |
| **Activation** | Wake word or hotkey | Always-on stream |
| **Speed** | ~2–3s after speaking | Near-instant |
| **Internet** | ❌ 100% offline | ✅ Gemini API |
| **Privacy** | Audio never leaves machine | Audio goes to Google |

**Wake phrases:** `"Hey Zeno"` · `"Okay Zeno"` · `"Yo Zeno"` · `"Hi Zen"` · `"Hello Zeno"` · `"Hey Zenith"`

**Hotkeys:** `Ctrl+Shift+Space` — brain dump overlay · `Ctrl+Shift+J` — push-to-talk

**Dual-path wake detection:**
- **Acoustic path** — `openWakeWord` fires instantly on audio signature
- **Transcript path** — `Whisper-tiny` + `WebRTC VAD` scans every 1.5s as fallback (mode 2, consecutive-frame speech gate)

### 📋 Task Management
- Add, update, complete, defer, and flag tasks by voice
- Priorities (`high` · `medium` · `low`), due dates, project tags, blockers
- Full task lifecycle audit trail in SQLite
- *"Hey Zeno, what are my high-priority tasks for today?"*

### ⏰ Reminders & Scheduling
- One-time, recurring, and context-sensitive reminders
- Full calendar scheduling with time blocks
- APScheduler-powered — works even when the HUD is closed
- Real-time toast notifications pushed to the HUD

### 🗂️ Session Management
- Tracks daily work sessions with memory state
- Shutdown ritual saves a session summary
- Resumes with context — pending items and all

### 💼 Workspace Macros
- Define multi-step workspace setups in `workspaces.yaml`
- *"Hey Zeno, start my coding workspace"* → launches VS Code, opens GitHub, toggles DND
- **Step types:** `open_app` · `open_url` · `focus_window` · `arrange_windows` · `toggle_dnd` · `announce` · `wait_ms`

### 🦆 Rubber Duck Mode — AI-Powered Problem Solving
A Socratic conversation that guides you through a problem and generates a full PRD document with extracted tasks.

```
You:  "Hey Zeno, start rubber duck mode"
Zeno: "What's the problem you're trying to solve?"
...   [6-phase guided conversation]
Zeno: "PRD.md generated at ~/Zeno/projects/my-feature/"
      "I've extracted 7 tasks and added them to your task list."
```

**Phases:** `PROBLEM → CONSTRAINTS → EDGE_CASES → DEPENDENCIES → CRITERIA → GENERATING`

### 📊 Passive Activity Monitoring
- Samples your active window every **30 seconds**
- Detects context switches and off-task behavior
- Privacy: all window titles redacted against `privacy_exclusions`
- Feeds analytics and morning briefing pipelines

### 🌐 Browser Extension
- Tracks active tabs and domain dwell time via local WebSocket (port 8767)
- Supports Chrome, Firefox, Edge, Safari

### 📈 Analytics & Morning Briefing
- Daily briefings generated by Gemini — tasks, schedule, focus summary
- Weekly deep work and distraction breakdowns
- Visual charts in the HUD dashboard (Recharts)

### 📝 Notes with Full-Text Search
- *"Hey Zeno, note: check the API rate limits for prod"*
- FTS5-powered search across title, content, and tags

### 🔊 Text-to-Speech
| Engine | Type | Notes |
|--------|------|-------|
| `pyttsx3` | Offline | Default, zero latency, dedicated thread |
| `ElevenLabs` | Cloud (optional) | Premium, natural voice |
| `Coqui TTS` | Offline (optional) | High-quality local alternative |

---

## 🏗️ System Architecture

```
python -m zeno [--live]
│
├── OS Agent ──────── port 8765 ── 90+ desktop tools (FastAPI + uvicorn)
├── REST API ──────── port 8766 ── Tasks, memory, sessions, sudo confirm
├── WebSocket ─────── port 8767 ── State events → React HUD + browser ext
│
├─ [Whisper mode — offline]
│   ├── ZenoMicPump ────────── fan-out mic to 3 parallel queues
│   ├── ZenoAcousticBridge ── openWakeWord → wake_event  (Path A: fast)
│   ├── ZenoVadScanner ────── WebRTC VAD + Whisper-tiny  (Path B: reliable)
│   └── VoiceLoop ─────────── collect audio → Whisper-base → NLP/Gemini → TTS
│       └── AI Memory ──────── add_to_dialogue() + Gemini extraction post-turn
│
└─ [Live mode — --live]
    └── GeminiLiveSession ─── bidirectional real-time audio → Gemini → tools → TTS
```

### Voice Command Data Flow
```
Microphone
  → Dual-path wake detection (acoustic + WebRTC VAD transcript)
  → Speech transcription (Whisper-base STT)
  → Intent classification (NLP Parser, confidence ≥ 0.75)
  → Slot extraction (31 typed slot types)
  → Action Dispatcher → Handler (DB / OS tool / Gemini API)
  → AI Memory extraction (async post-turn)
  → TTS response → voice_interactions log
```

---

## 🧩 NLP Intent System

ZENO understands **52 named intents** across **10 categories** with **31 slot types**.

| Category | Example Intents |
|----------|----------------|
| **Task Management** | `add_task`, `update_task`, `complete_task`, `list_tasks` |
| **Session Control** | `start_session`, `end_session`, `resume_session` |
| **Scheduling** | `add_time_block`, `rebalance_schedule`, `query_schedule` |
| **Reminders** | `add_reminder`, `snooze_reminder`, `list_reminders` |
| **Workspace Macros** | `activate_workspace`, `save_workspace` |
| **Analytics** | `query_focus_time`, `query_distraction_report` |
| **Rubber Duck** | `start_rubber_duck`, `generate_prd` |
| **Notes** | `add_note`, `search_notes`, `read_note` |
| **Morning Briefing** | `deliver_briefing`, `start_day_planning` |
| **System Control** | `initiate_shutdown`, `toggle_dnd`, `check_status` |

---

## 💾 Database Schema

SQLite at `~/Zeno/Zeno.db` — WAL mode, 22 tables, 4 views, 7 triggers, 25+ indexes.

| Section | Tables | Purpose |
|---------|--------|---------|
| Core Identity | `user_profile`, `privacy_exclusions` | Config singleton, privacy blocklist |
| **Memory** | **`memories`** | **Persistent AI memory (7 categories, auto-extracted)** |
| Projects | `projects` | Registry with status, color, paths |
| Tasks | `tasks`, `task_dependencies`, `task_history` | Full lifecycle + audit trail |
| Sessions | `sessions`, `session_pending_items` | Daily sessions with memory state |
| Time Blocks | `time_blocks`, `schedule_reroutings` | Calendar scheduling |
| Reminders | `reminders` | One-time, recurring, contextual |
| Activity | `activity_log`, `browser_sessions`, `context_switches` | 30s passive samples |
| Analytics | `analytics_weekly`, `analytics_daily`, `behaviour_patterns` | Stats + patterns |
| Workspaces | `workspaces`, `workspace_steps`, `workspace_activations` | Macro profiles |
| Voice | `voice_interactions`, `conversations` | Full NLP interaction audit |
| Notes | `notes` + FTS5 virtual table | Searchable brain dumps |
| Rubber Duck | `rubber_duck_sessions` | Socratic planning sessions |
| App Class | `app_classifications` | Work/off-task whitelist |
| System | `system_events`, `schema_version` | Audit log + migrations |

---

## 🛠️ Technology Stack

### Backend (Python 3.11+)
| Package | Purpose |
|---------|---------|
| `google-genai` | Gemini 2.0 Flash — reasoning, memory extraction, Live voice |
| `openai-whisper` | Local offline speech-to-text |
| `openwakeword` | Acoustic wake word detection |
| `webrtcvad` | Voice activity detection (consecutive-frame speech gating) |
| `fastapi` + `uvicorn` | REST API (port 8766) + OS Agent (port 8765) |
| `websockets` | WebSocket server (port 8767) — state events, browser ext |
| `apscheduler` | Reminders, briefings, scheduled jobs |
| `pyttsx3` | Default offline TTS (dedicated COM thread on Windows) |
| `sounddevice` | Microphone capture (fan-out to multiple consumer queues) |
| `rapidfuzz` | Fuzzy wake phrase and task name matching |
| `psutil` | System metrics (CPU, RAM, battery) |
| `pyyaml` | Config and workspace macro parsing |
| `pygetwindow` + `pywin32` | Window management on Windows |

### Frontend (React 19 + Tauri 2)
| Package | Purpose |
|---------|---------|
| `@tauri-apps/api` | IPC, window management, system tray |
| `react` + `react-dom` | Sci-fi HUD UI |
| `vite` | Build tool |
| `recharts` | Analytics charts |
| `lucide-react` | Icon library (Memory Dashboard, SudoPopup, etc.) |
| Vanilla CSS | Custom HUD design (Orbitron, Share Tech Mono fonts) |

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.11+**
- **Rust + Cargo** (for Tauri desktop shell)
- **Node.js 18+** (for frontend)
- A **Google Gemini API key** (free tier at [ai.google.dev](https://ai.google.dev))
- A working microphone

### 1. Clone the repository

```bash
git clone https://github.com/VarunRathore137/ZENO-Agent.git
cd ZENO-Agent
```

### 2. Set up the Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure your API key

```powershell
# Windows (PowerShell)
$env:GOOGLE_API_KEY = "your-gemini-api-key-here"

# macOS / Linux
export GOOGLE_API_KEY="your-gemini-api-key-here"
```

### 4. Initialize the database

```bash
python scripts/init_db.py
```

### 5. Run ZENO

```bash
# Offline mode — Whisper STT, 100% private
python -m zeno

# Live mode — Gemini real-time voice (requires GOOGLE_API_KEY)
python -m zeno --live
```

You'll see:
```
ZENO daemon initializing... [WHISPER MODE]
[ZENO] 🛠️  OS Agent running on port 8765 — 91 tools available.
[ZENO] Running in WHISPER mode.
  OS Agent: port 8765  |  API: port 8766  |  WS: port 8767
  Say 'Hey Zeno' to give a voice command. Press Ctrl+C to stop.
```

### 6. Run the frontend HUD (optional)

```bash
cd frontend
npm install
npm run dev
```

Or build the full Tauri desktop app:

```bash
cd src-tauri
cargo tauri dev
```

---

## ⚙️ Configuration

### `~/Zeno/config.yaml`

```yaml
zeno:
  wake_word: ["Hey Zeno", "Okay Zeno", "Hi Zen"]
  tts_engine: pyttsx3          # pyttsx3 | elevenlabs | coqui
  stt_model: whisper-base      # whisper-tiny | whisper-base | whisper-small
  timezone: Asia/Kolkata
  working_hours_start: "09:00"
  working_hours_end: "21:00"
  morning_briefing_time: "08:30"
```

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_API_KEY` | ✅ Yes | Gemini API — AI fallback, memory extraction, Live mode |
| `ZENO_VOICE_MODE` | Optional | Set to `"live"` to start in Live mode without `--live` flag |
| `ZENO_DEBUG` | Optional | Set to `"1"` to enable verbose debug logging |
| `ZENO_AGENT_PORT` | Optional | Override OS Agent port (default: `8765`) |
| `ELEVENLABS_API_KEY` | Optional | ElevenLabs TTS (only if `tts_engine: elevenlabs`) |

### Workspace Macros (`~/Zeno/workspaces.yaml`)

```yaml
workspaces:
  - name: coding
    trigger: "start coding workspace"
    steps:
      - type: open_app
        app: "Code"
      - type: open_url
        url: "https://github.com"
      - type: toggle_dnd
        enabled: true
      - type: announce
        message: "Coding workspace is ready. Let's build."
```

---

## 🗣️ Example Voice Commands

```
# App Control
"Hey Zeno, open Spotify"
"Hey Zeno, open Chrome"
"Hey Zeno, close Discord"

# Tasks
"Hey Zeno, add task: fix the login bug — high priority, due Friday"
"Hey Zeno, what are my tasks for today?"
"Hey Zeno, mark the login bug as done"

# Notes & Brain Dump
"Hey Zeno, note: check the API rate limits before deploying"
"Hey Zeno, search my notes for Redis"

# System
"Hey Zeno, volume up"
"Hey Zeno, take a screenshot"
"Hey Zeno, read my screen"

# Workspaces
"Hey Zeno, start my coding workspace"

# AI Conversations (Gemini fallback)
"Hey Zeno, explain how async generators work"
"Hey Zeno, tell me a joke"

# Planning
"Hey Zeno, start rubber duck mode"     ← generates full PRD
"Hey Zeno, what's my schedule today?"
"Hey Zeno, I'm done for the day"       ← shutdown ritual
```

---

## 📁 Project Structure

```
ZENO-Agent/
├── zeno/                    # Python backend daemon
│   ├── ai/                  # LLM engine (memory, briefings, rubber duck, PRD)
│   │   ├── memory.py        # Persistent AI memory — 7-category extraction & injection
│   │   ├── gemini_live.py   # Gemini Live bidirectional streaming voice
│   │   ├── providers.py     # LLM provider routing (Gemini / Claude)
│   │   ├── briefing.py      # Morning briefing generator
│   │   ├── rubber_duck.py   # 6-state Socratic problem-solving machine
│   │   ├── prd_writer.py    # PRD generation + task extraction
│   │   └── prompts.py       # YAML-based prompt loader
│   ├── agent/               # OS tool agent
│   │   ├── server.py        # FastAPI tool server (port 8765)
│   │   ├── dispatch.py      # Tool call dispatcher
│   │   ├── registry.py      # Tool registration
│   │   ├── backends/        # OS backends (Windows, macOS, Linux, Wayland)
│   │   └── tools/           # 90+ OS tools
│   │       ├── applications.py   # App launch/close + dynamic path resolution
│   │       ├── browser.py        # Browser + URL control
│   │       ├── system.py         # CPU, RAM, GPU metrics
│   │       ├── terminal.py       # Terminal execution (with blacklist + SudoPopup)
│   │       ├── screenshot.py     # Screenshot + Tesseract OCR screen reading
│   │       ├── windows.py        # Window management
│   │       └── ...               # clipboard, files, weather, news, etc.
│   ├── api/                 # FastAPI REST server (port 8766)
│   ├── dispatcher/          # Intent → handler routing
│   ├── handlers/            # Tasks, notes, reminders, sessions, workspaces
│   ├── monitor/             # Activity monitor + WebSocket server (port 8767)
│   ├── nlp/                 # Intent classifier + slot extractor
│   ├── scheduler/           # APScheduler jobs
│   ├── tts/                 # TTS engine + provider adapters
│   ├── voice/               # Voice pipeline
│   │   ├── capture.py       # Mic fan-out to multiple queues
│   │   ├── wake_word.py     # Wake detection (acoustic + fuzzy transcript)
│   │   ├── transcriber.py   # Whisper STT
│   │   ├── hotkeys.py       # Global hotkeys
│   │   └── gemini_live.py   # Gemini Live streaming session
│   └── __main__.py          # Daemon entry point (dual wake, TTS thread, WS broadcast)
├── frontend/                # React + Vite sci-fi HUD
│   └── src/
│       ├── components/
│       │   ├── ArcReactor.tsx         # Primary state visualizer
│       │   ├── CharacterVisualizer.tsx # Anime/video character overlay
│       │   ├── MemoryDashboard.tsx    # AI memory browser & editor
│       │   ├── SudoPopup.tsx          # Elevated command authorization modal
│       │   ├── Toast.tsx              # Real-time reminder toasts
│       │   ├── Dashboard.tsx          # Analytics HUD
│       │   └── Settings.tsx           # ZENO settings panel
│       └── hooks/
│           ├── useDaemonWs.ts         # WebSocket state hook (port 8767)
│           └── useApi.ts              # REST API hook (port 8766)
├── src-tauri/               # Rust Tauri native shell (system tray, autostart)
├── scripts/                 # Setup scripts
├── zeno_usage_guide.md      # Complete command reference
├── ZENO_Testing_Cheatsheet.md
├── requirements.txt
└── ARCHITECTURE.md
```

---

## 🔒 Privacy & Security

- ✅ **All data stored locally** — no cloud database, no telemetry
- ✅ **Whisper mode is 100% offline** — audio never leaves your machine
- ✅ **Window titles and browser domains redacted** against `privacy_exclusions`
- ✅ **API keys from environment variables only** — never stored in files
- ✅ **Macro engine uses an app whitelist** — no arbitrary shell execution
- ✅ **Destructive terminal commands** require a two-phase SudoPopup confirmation with a timer
- ✅ **External calls limited to:** Google Gemini (AI reasoning + Live voice) and optionally ElevenLabs (TTS)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push to the branch: `git push origin feat/your-feature`
5. Open a Pull Request

Please follow the existing code style (Black + Ruff for Python, TypeScript strict mode for frontend).

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by [Varun Rathore](https://github.com/VarunRathore137)**

*ZENO 2.0 — Because your assistant should actually understand you.*

</div>
