# ZENO 2.0 — Complete Usage Guide

> Everything here is accurate to your actual codebase as it stands today.

---

## How to Start ZENO

Open a terminal (PowerShell or VS Code terminal) in your project folder and run one of:

```powershell
# Default mode — fully offline, private, uses Whisper for speech-to-text
python -m zeno

# Live mode — Gemini real-time voice (faster, more natural, needs internet)
python -m zeno --live
```

**What you'll see when it starts:**

```
ZENO daemon initializing... [WHISPER MODE]
[ZENO] 🛠️  OS Agent running on port 8765 — 92 tools available.
[ZENO] Running in WHISPER mode.
  OS Agent: port 8765  |  API: port 8766  |  WS: port 8767
  Say 'Hey Zeno' to give a voice command. Press Ctrl+C to stop.
```

---

## Two Voice Modes

| | Whisper Mode (Default) | Live Mode (`--live`) |
|---|---|---|
| **Start command** | `python -m zeno` | `python -m zeno --live` |
| **How it hears you** | Wake word → records 6s → Whisper STT | Always-on real-time stream |
| **Speed** | ~2–3 second delay after you speak | Near-instant response |
| **Internet needed** | ❌ No (Whisper runs fully locally) | ✅ Yes (Gemini API) |
| **Wake phrase** | "Hey Zeno" (see list below) | Just start speaking |
| **Tools** | Same 92 OS tools via dispatcher | Same 92 tools via Gemini function calling |
| **Privacy** | 100% local audio processing | Audio goes to Google servers |

---

## Wake Phrases (Whisper Mode)

Any of these will activate ZENO and start listening for your command:

```
"Hey Zeno"          "Okay Zeno"         "OK Zeno"
"Yo Zeno"           "Hi Zeno"           "Hello Zeno"
"Hey Zen"           "Hi Zen"            "Wake up Zeno"
"Zeno wake up"      "Hey Zenith"        "OK Zenith"
```

> The wake system has two detection paths:
> - **Acoustic path** (fast): openWakeWord model fires instantly
> - **Transcript path** (reliable): Whisper-tiny scans every 2.5s as a fallback
>
> Either path triggers a 6-second command recording window. Speak your command after the wake word.

---

## All Automatable Commands

### 🗂️ Task Management (SQLite-backed)

| What you say | What ZENO does |
|---|---|
| `"Add task fix the login bug"` | Creates task in Zeno.db |
| `"New task: review PR 47"` | Creates task |
| `"What are my tasks for today?"` | Lists pending tasks by priority |
| `"What high priority tasks are pending?"` | Filters by priority |
| `"Mark the login bug as done"` | Completes the matching task |
| `"I finished writing the API docs"` | Completes the matching task |
| `"Change the deadline on the report to Thursday"` | Updates task deadline |

---

### 📅 Day Planning

| What you say | What ZENO does |
|---|---|
| `"Let's plan my day"` | Starts an interactive day planning session |
| `"What's my schedule for today?"` | Shows today's scheduled events |
| `"When's my next meeting?"` | Shows next calendar event |

---

### 📝 Notes & Ideas

| What you say | What ZENO does |
|---|---|
| `"Note: the API should use pagination"` | Saves idea to Zeno.db |
| `"Save this idea: use Redis for caching"` | Saves idea |
| `"Brain dump: need to refactor auth module"` | Saves idea |
| `"Search my notes for Redis"` | Full-text search across all notes |
| `"Find my note about authentication"` | Searches notes |

---

### ⏰ Reminders

| What you say | What ZENO does |
|---|---|
| `"Remind me in 30 minutes to take a break"` | Sets timer-based reminder |
| `"Set a reminder for the standup at 10am"` | Sets time-based reminder |
| `"Alert me in an hour"` | Sets 60-minute reminder |
| `"What reminders do I have?"` | Lists active reminders |

---

### 🖥️ App Control

| What you say | What ZENO does |
|---|---|
| `"Open Chrome"` | Launches Google Chrome |
| `"Launch VS Code"` | Opens Visual Studio Code |
| `"Open Spotify"` | Launches Spotify |
| `"Start the terminal"` | Opens Command Prompt |
| `"Open File Explorer"` | Opens Windows Explorer |
| `"Open Discord"` | Launches Discord |
| `"Open Calculator"` | Opens the Calculator |
| `"Open Notepad"` | Opens Notepad |
| `"Open PowerShell"` | Launches PowerShell |
| `"Open Settings"` | Opens Windows Settings |
| `"Open Task Manager"` | Opens Task Manager |
| `"Close Chrome"` | Closes Chrome |
| `"Kill VS Code"` | Closes VS Code |

**Full list of recognized apps:** Calculator, Chrome, Edge, File Explorer, Notepad, Notepad, Paint, PowerShell, Settings, Snipping Tool, Spotify, Task Manager, Terminal/CMD, VS Code, WordPad

---

### 🌐 Web & Search

| What you say | What ZENO does |
|---|---|
| `"Open YouTube"` | Opens YouTube in browser |
| `"Go to GitHub"` | Navigates to GitHub |
| `"Open Gmail"` | Opens Gmail |
| `"Open Reddit"` | Opens Reddit |
| `"Search the web for Python async tips"` | Google search |
| `"Look up React hooks tutorial"` | Google search |
| `"Search YouTube for Lo-fi music"` | YouTube search |
| `"Find on YouTube: system design interview"` | YouTube search |

---

### 🔊 Volume & Brightness

| What you say | What ZENO does |
|---|---|
| `"Volume up"` | Raises volume by 10% |
| `"Volume down"` | Lowers volume by 10% |
| `"Mute"` | Toggles mute on/off |
| `"Set volume to 50"` | Sets exact volume to 50% |
| `"Brightness up"` | Raises screen brightness by 10% |
| `"Brightness down"` | Lowers brightness by 10% |

---

### 🖼️ Window Management

| What you say | What ZENO does |
|---|---|
| `"Minimize Chrome"` | Minimizes the Chrome window |
| `"Maximize VS Code"` | Maximizes VS Code |
| `"Close the window"` | Closes the foreground window |
| `"Switch to Chrome"` | Brings Chrome to foreground |

---

### 📋 Clipboard

| What you say | What ZENO does |
|---|---|
| `"What's in my clipboard?"` | Reads and speaks clipboard contents |
| `"Read clipboard"` | Same |
| `"Paste clipboard"` | Pastes current clipboard into focused app |

---

### 📸 Screenshot & Screen Vision

| What you say | What ZENO does |
|---|---|
| `"Take a screenshot"` | Captures full screen |
| `"Save a screenshot"` | Saves PNG to `~/Pictures/ZenoScreenshots/` |
| `"Read my screen"` | OCR of the active window — reads text aloud |
| `"What's on my screen?"` | Same as above |
| `"What does the screen say?"` | Same as above |

> Uses Tesseract OCR at `C:\Program Files\Tesseract-OCR\tesseract.exe` (v5.5.3) — already installed and verified ✅

---

### 💻 System Info

| What you say | What ZENO does |
|---|---|
| `"System info"` | Reports CPU, RAM, disk usage |
| `"How's my CPU?"` | CPU percent usage |
| `"Check RAM usage"` | Memory usage |
| `"What's my disk space?"` | Disk usage |
| `"GPU info"` | GPU stats (if NVIDIA) |

---

### 🌦️ Weather & News

| What you say | What ZENO does |
|---|---|
| `"What's the weather?"` | Current weather (default location) |
| `"Weather in Mumbai"` | Weather for specific city |
| `"Is it going to rain?"` | Precipitation forecast |
| `"What's in the news?"` | Top headlines |
| `"Tech news"` | Technology category news |
| `"Latest technology news"` | Same |

---

### 🖱️ OS Input Control

| What you say | What ZENO does |
|---|---|
| `"Type hello world"` | Types text using keyboard simulation |
| `"Press enter"` | Simulates Enter key |
| `"Press escape"` | Simulates Escape key |
| `"Click at 500 300"` | Moves mouse and clicks at screen coordinates |

---

### 💻 Terminal Commands

| What you say | What ZENO does |
|---|---|
| `"Run git status"` | Executes `git status` in terminal |
| `"Run command pip list"` | Runs any shell command |
| `"Execute npm start"` | Runs `npm start` |
| `"Run in terminal: python script.py"` | Runs python file |

> ⚠️ **Safety blacklist active** — destructive commands are blocked automatically:
> `rm -rf /`, `format c:`, `diskpart`, `del /f /s /q`, and many others.
> Sudo commands require a second confirmation step.

---

### ☁️ Google Suite (after OAuth setup)

| What you say | What ZENO does |
|---|---|
| `"What's on my calendar?"` | Lists upcoming events (next 7 days) |
| `"Any meetings today?"` | Same, filtered to today |
| `"What events do I have this week?"` | Week's calendar events |
| `"Check my email"` | Reads 5 latest Gmail inbox emails |
| `"Any new emails?"` | Same |
| `"Send an email to John"` | Starts email composition |

> **Status:** `credentials.json` is in place at `C:\Users\LENOVO\Zeno\google_oauth\credentials.json`.
> Run `python -m zeno.agent.tools.google` once to authorize and activate.

---

### 📁 File Operations

| What you say | What ZENO does |
|---|---|
| `"Create a file notes.txt"` | Creates file in safe folders |
| `"Read file report.md"` | Reads file contents aloud |
| `"List my files"` | Lists files in current/home directory |
| `"Search my files for invoice"` | Searches file names |
| `"Delete notes.txt"` | Moves to Recycle Bin (safe delete) |

> Files are restricted to: Desktop, Documents, Downloads, Pictures, Music, Videos. System paths are blocked.

---

### 🧰 Workspaces (App Launch Macros)

| What you say | What ZENO does |
|---|---|
| `"Set up coding workspace"` | Launches VS Code, opens GitHub in browser, maximizes VS Code, enables DND |
| `"Set up writing workspace"` | Opens Notion, enables DND |
| `"List my workspaces"` | Lists all configured workspaces |

**Add custom workspaces** by editing:
```
C:\Users\LENOVO\Zeno\workspaces.yaml
```
Supported step types: `open_app`, `open_url`, `focus_window`, `arrange_windows`, `toggle_dnd`, `announce`, `wait_ms`

---

### 🤖 Conversational AI Fallback

When ZENO doesn't recognize a structured command, it **automatically falls back to Gemini** for a free-form conversation. No special trigger needed:

- *"Hey Zeno, explain how async generators work in Python"* → Full Gemini explanation
- *"Tell me a joke"* → Gemini responds
- *"What's the time complexity of quicksort?"* → Gemini answers
- *"Hey Zeno, how's it going?"* → Casual chat

Responses are kept under 3 sentences for voice output.

---

### 🧠 AI Memory (Automatic)

ZENO automatically learns about you over time. After each conversation turn, it uses Gemini to extract durable facts and saves them to `Zeno.db`.

**What it remembers (7 categories):**
1. **Identity** — your name, role, background
2. **Preferences** — your likes, dislikes, habits
3. **Goals** — what you're working toward
4. **Projects** — ongoing projects and their status
5. **Relationships** — people in your life
6. **Emotional** — mood patterns, milestones
7. **Behavior** — patterns and routines

Memory is injected naturally into every conversation — ZENO knows your context without you having to repeat yourself. Up to 100 memories stored, pruned by recency.

---

### 🔋 Power Actions (Gated — need confirmation)

Power actions require a 2-step confirmation for safety:

1. Say: `"Shut down my computer"` → ZENO issues a confirmation token
2. Confirm: `"Yes, execute shutdown"` → ZENO runs `shutdown /s /t 10`

Actions: **shutdown**, **restart**, **sleep**, **lock**

---

## File Locations (Everything ZENO stores)

| What | Where |
|---|---|
| Database (tasks, notes, etc.) | `C:\Users\LENOVO\Zeno\Zeno.db` |
| Config file | `C:\Users\LENOVO\Zeno\config.yaml` |
| Workspaces config | `C:\Users\LENOVO\Zeno\workspaces.yaml` |
| Google OAuth credentials | `C:\Users\LENOVO\Zeno\google_oauth\credentials.json` |
| Google OAuth token | `C:\Users\LENOVO\Zeno\google_oauth\token.pickle` |
| Screenshots | `C:\Users\LENOVO\Pictures\ZenoScreenshots\` |
| ZENO logs | `C:\Users\LENOVO\Zeno\logs\` |
| Conversation exports | `C:\Users\LENOVO\Zeno\sessions\` |

---

## Ports (What's running in background)

| Port | Service | Purpose |
|---|---|---|
| **8765** | OS Agent (FastAPI) | Desktop tool dispatcher — 92 tools |
| **8766** | REST API (FastAPI) | ZENO's internal REST endpoints |
| **8767** | WebSocket Server | Browser extension integration |

---

## Environment Variables You Can Set

```powershell
$env:GOOGLE_API_KEY = "your-key-here"      # Required for Gemini fallback and Live mode
$env:ZENO_VOICE_MODE = "live"              # Start in live mode without --live flag
$env:ZENO_DEBUG = "1"                      # Enable debug logging
$env:ZENO_AGENT_PORT = "8765"              # Change OS Agent port (default: 8765)
```

---

## Quick Start Checklist

- [x] ZENO installed and all imports working
- [x] OS Agent — 92 tools registered and tested
- [x] Whisper STT — local voice recognition
- [x] Gemini AI fallback — free-form conversation
- [x] Tesseract OCR — screen reading (v5.5.3 at `C:\Program Files\Tesseract-OCR\`)
- [x] AI Memory system — persistent across sessions in SQLite
- [ ] Google Suite — `credentials.json` placed ✅, needs one-time browser authorization
- [ ] Gemini Live mode — needs `GOOGLE_API_KEY` set

---

## What's Not Yet Built (Phase 5 — UI)

These are backend-complete but the UI hasn't been upgraded yet:
- Visual state machine in the overlay (idle / thinking / talking animations)
- Memory Dashboard — see/edit what ZENO remembers about you
- Reminder toast notifications
- Dangerous action confirmation popup (`SudoPopup`)
- Optional: Anime character toggle alongside the ArcReactor
