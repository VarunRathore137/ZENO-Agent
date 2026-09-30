"""
zeno/voice/gemini_live.py
─────────────────────────
Gemini Live API voice session for ZENO.

Provides bidirectional real-time audio streaming using google-genai SDK.
Activated when ZENO_VOICE_MODE=live or --live flag is passed.

Architecture:
  MicrophoneStream → PCM encoder → Gemini Live WebSocket
  Gemini Live WebSocket → PCM decoder → Speaker output
  Function calls from Gemini → ZENO dispatcher → response back to session

Usage:
    session = GeminiLiveSession(api_key=..., db_path=...)
    asyncio.run(session.run())
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from google import genai as _genai
from google.genai import types as gtypes

log = logging.getLogger("zeno.voice.live")

# Module-level import so _receive_loop / stop() can use it directly
try:
    from zeno.monitor.ws_server import broadcast_state
except Exception:
    def broadcast_state(state: str) -> None:  # type: ignore[misc]
        pass

# ────────────────────────────────────────────────────────────────────
# ZENO system prompt for Gemini Live
# ────────────────────────────────────────────────────────────────────
_ZENO_LIVE_SYSTEM_PROMPT = """You are ZENO (Zenith Engine for Neural Orchestration), a voice-first personal AI assistant for a software engineer and developer.

PERSONALITY:
- You are concise, sharp, and friendly — a brilliant AI companion, not a corporate chatbot.
- You speak naturally and conversationally. Keep responses short (1-3 sentences) unless asked to elaborate.
- You are knowledgeable about software engineering, productivity, and developer tools.
- You have personality: you can be witty, but you stay professional and useful.

CAPABILITIES:
You have access to powerful tools that let you control the user's computer:
- Open and close applications (VS Code, Chrome, Terminal, etc.)
- Control system volume, brightness, and power
- Read and write files, run terminal commands
- Search the web, YouTube, GitHub
- Take screenshots and read what's on screen via OCR
- Manage Google Calendar, Gmail, and Tasks
- Get weather and news
- Control browser automation (navigate, click, type, fill forms)

BEHAVIOR:
- When the user asks you to DO something (open an app, run a command, search something), USE THE TOOLS. Don't just describe how to do it.
- When a tool requires confirmation (like shutdown), always ask first.
- Never run dangerous terminal commands — they are blocked at the system level.
- For tasks, notes, reminders: these are handled by ZENO's local database system. Confirm when done.
- Keep your spoken responses short — the user is listening, not reading.

MEMORY:
You have access to persistent memory about this user. Use it naturally in conversation without robotic references like "According to my records..." — just speak like you know them."""

# ────────────────────────────────────────────────────────────────────
# Function declarations for Gemini Live
# These map to ZENO's OS agent tools
# ────────────────────────────────────────────────────────────────────
ZENO_TOOL_DECLARATIONS = [
    # Applications
    {"name": "openApplication", "description": "Open an application on the desktop.", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "App name: chrome, vscode, terminal, notepad, calculator, spotify, etc."}}, "required": ["name"]}},
    {"name": "closeApplication", "description": "Close a running application.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "force": {"type": "boolean", "default": False}}, "required": ["name"]}},

    # Browser & search
    {"name": "openWebsite", "description": "Open a website by name or URL.", "parameters": {"type": "object", "properties": {"name": {"type": "string", "description": "Site name (youtube, github, gmail) or full URL"}}, "required": ["name"]}},
    {"name": "searchWeb", "description": "Search the web.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "searchYouTube", "description": "Search YouTube.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "searchGoogle", "description": "Search Google.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "searchGitHub", "description": "Search GitHub.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},

    # Browser automation
    {"name": "desktopBrowserOpen", "description": "Open a URL in the automated browser.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "desktopBrowserSearch", "description": "Search in the automated browser.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "desktopBrowserClick", "description": "Click an element on a browser page.", "parameters": {"type": "object", "properties": {"selector": {"type": "string", "description": "CSS selector or element description"}}, "required": ["selector"]}},
    {"name": "desktopBrowserType", "description": "Type text into a browser element.", "parameters": {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}}, "required": ["selector", "text"]}},
    {"name": "desktopBrowserReadText", "description": "Read the text content of the current browser page.", "parameters": {"type": "object", "properties": {}}},
    {"name": "desktopBrowserScroll", "description": "Scroll the browser page.", "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"]}, "amount": {"type": "integer", "default": 300}}, "required": ["direction"]}},

    # Files
    {"name": "createFile", "description": "Create a new file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string", "default": ""}}, "required": ["filename"]}},
    {"name": "readFile", "description": "Read the contents of a file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}},
    {"name": "deleteFile", "description": "Delete a file (moves to trash by default).", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "permanent": {"type": "boolean", "default": False}}, "required": ["filename"]}},
    {"name": "listFiles", "description": "List files in a directory.", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "default": "~"}}}},
    {"name": "searchFiles", "description": "Search for files by name or content.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},

    # System control
    {"name": "volumeUp", "description": "Increase system volume.", "parameters": {"type": "object", "properties": {}}},
    {"name": "volumeDown", "description": "Decrease system volume.", "parameters": {"type": "object", "properties": {}}},
    {"name": "setVolume", "description": "Set system volume to a specific level.", "parameters": {"type": "object", "properties": {"level": {"type": "integer", "description": "0-100"}}, "required": ["level"]}},
    {"name": "muteToggle", "description": "Toggle mute on/off.", "parameters": {"type": "object", "properties": {}}},
    {"name": "setBrightness", "description": "Set screen brightness.", "parameters": {"type": "object", "properties": {"level": {"type": "integer", "description": "0-100"}}, "required": ["level"]}},
    {"name": "systemInfo", "description": "Get CPU, RAM, disk usage information.", "parameters": {"type": "object", "properties": {}}},
    {"name": "gpuInfo", "description": "Get GPU information and temperature.", "parameters": {"type": "object", "properties": {}}},

    # Power (2-step gated)
    {"name": "requestPowerAction", "description": "Request a power action (shutdown, restart, sleep, lock). Returns a token for confirmation.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["shutdown", "restart", "sleep", "lock", "hibernate"]}}, "required": ["action"]}},
    {"name": "executePowerAction", "description": "Execute a gated power action using the confirmation token.", "parameters": {"type": "object", "properties": {"token": {"type": "string"}, "action": {"type": "string"}}, "required": ["token", "action"]}},

    # Screenshot & OCR
    {"name": "takeScreenshot", "description": "Take a screenshot of the current screen.", "parameters": {"type": "object", "properties": {}}},
    {"name": "readScreen", "description": "Take a screenshot and read the text on screen using OCR.", "parameters": {"type": "object", "properties": {}}},
    {"name": "analyzeScreenshot", "description": "Take a screenshot and describe what's visible.", "parameters": {"type": "object", "properties": {}}},

    # Clipboard
    {"name": "getClipboard", "description": "Read the current clipboard contents.", "parameters": {"type": "object", "properties": {}}},
    {"name": "copySelected", "description": "Copy the currently selected text to clipboard.", "parameters": {"type": "object", "properties": {}}},
    {"name": "pasteClipboard", "description": "Paste clipboard contents.", "parameters": {"type": "object", "properties": {}}},

    # Windows
    {"name": "minimizeWindow", "description": "Minimize a window by title.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "maximizeWindow", "description": "Maximize a window by title.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "closeWindow", "description": "Close a window by title.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "switchApplication", "description": "Switch focus to an application.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},

    # Terminal (blacklisted commands blocked at agent level)
    {"name": "requestTerminalAction", "description": "Request execution of a terminal command. Returns a token for confirmation.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "runTerminalCommand", "description": "Run a terminal command.", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},

    # Coding
    {"name": "createPythonFile", "description": "Create a Python script file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["filename"]}},
    {"name": "runPythonScript", "description": "Run a Python script.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}},
    {"name": "writeCodeFile", "description": "Create a code file in any language.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}, "language": {"type": "string"}}, "required": ["filename", "content"]}},
    {"name": "createProjectFolder", "description": "Create a new project folder structure.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "template": {"type": "string", "default": "basic"}}, "required": ["name"]}},

    # OS input simulation
    {"name": "osType", "description": "Type text using keyboard simulation.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "osPress", "description": "Press a keyboard key or shortcut.", "parameters": {"type": "object", "properties": {"key": {"type": "string", "description": "e.g. 'enter', 'ctrl+c', 'alt+tab'"}}, "required": ["key"]}},
    {"name": "osClick", "description": "Click at a screen position or on an element.", "parameters": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}},

    # Weather & news
    {"name": "getWeather", "description": "Get current weather.", "parameters": {"type": "object", "properties": {"location": {"type": "string", "default": ""}}}},
    {"name": "getNews", "description": "Get top news headlines.", "parameters": {"type": "object", "properties": {"category": {"type": "string", "enum": ["general", "technology", "science", "sports", "business", "health", "entertainment"], "default": "technology"}}}},

    # Google Suite
    {"name": "getCalendarEvents", "description": "Get upcoming calendar events.", "parameters": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}},
    {"name": "createCalendarEvent", "description": "Create a Google Calendar event.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "description": {"type": "string", "default": ""}}, "required": ["title", "start_time", "end_time"]}},
    {"name": "sendEmail", "description": "Send an email via Gmail.", "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}},
    {"name": "getEmails", "description": "Get recent emails from Gmail.", "parameters": {"type": "object", "properties": {"max": {"type": "integer", "default": 5}}}},
    {"name": "getTasks", "description": "Get Google Tasks.", "parameters": {"type": "object", "properties": {}}},
    {"name": "createTask", "description": "Create a Google Task.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "due": {"type": "string", "description": "ISO date string"}}, "required": ["title"]}},

    # Memory
    {"name": "saveCustomMemory", "description": "Save a specific fact to ZENO's persistent memory.", "parameters": {"type": "object", "properties": {"category": {"type": "string", "enum": ["identity", "preference", "goal", "project", "relationship", "emotional", "behavior"]}, "text": {"type": "string"}}, "required": ["category", "text"]}},
]

# ────────────────────────────────────────────────────────────────────
# OS agent tool names (dispatched to agent subprocess)
# ────────────────────────────────────────────────────────────────────
_AGENT_TOOLS = {d["name"] for d in ZENO_TOOL_DECLARATIONS} - {"saveCustomMemory"}


def _call_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Route a Gemini function call to the correct handler.
    Returns a string result for Gemini.
    """
    # Special: memory save handled locally
    if tool_name == "saveCustomMemory":
        try:
            from zeno.ai.memory import save_memory_item
            save_memory_item(args.get("category", "behavior"), args.get("text", ""))
            return "Memory saved."
        except Exception as e:
            return f"Memory save failed: {e}"

    # All other tools → OS agent
    try:
        from zeno.agent.dispatch import dispatch_to_agent, is_agent_available
        if not is_agent_available():
            return "OS Agent is not running. Cannot execute desktop tools right now."
        result = dispatch_to_agent(tool_name, args)
        if isinstance(result, dict):
            return result.get("result") or result.get("output") or "Done."
        return str(result) or "Done."
    except RuntimeError as e:
        return f"Tool error: {e}"


# ────────────────────────────────────────────────────────────────────
# GeminiLiveSession
# ────────────────────────────────────────────────────────────────────
class GeminiLiveSession:
    """
    Manages a real-time bidirectional audio session with Gemini Live.

    Audio pipeline:
      MicrophoneStream → PCM int16 → Gemini (upstream)
      Gemini audio chunks → PCM int16 → Speaker (downstream)

    Function calls from Gemini are intercepted, dispatched to ZENO tools,
    and results fed back to the session automatically.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_path: Optional[str] = None,
        voice: str = "Charon",
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        self.db_path = db_path
        self.voice = voice
        self.model = model or os.environ.get("ZENO_LIVE_MODEL", "gemini-2.5-flash-native-audio-latest")
        self._stop = threading.Event()

    async def run(self) -> None:
        """Main entry point — starts the live session loop."""
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY must be set for Gemini Live mode. "
                "Set ZENO_VOICE_MODE=whisper to use offline mode instead."
            )

        log.info("Starting Gemini Live session (model=%s, voice=%s)", self.model, self.voice)
        print(
            f"[ZENO] 🎙️ Gemini Live mode active — say 'Hey Zeno' to begin.\n"
            f"       Model: {self.model}  Voice: {self.voice}\n"
            f"       Press Ctrl+C to stop.",
            flush=True,
        )

        client = _genai.Client(api_key=self.api_key)

        # Build system prompt with memory injection
        system_prompt = await self._build_system_prompt()

        # Build tool config from declarations
        tools = [
            gtypes.Tool(
                function_declarations=[
                    gtypes.FunctionDeclaration(**decl)
                    for decl in ZENO_TOOL_DECLARATIONS
                ]
            )
        ]

        live_config = gtypes.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=gtypes.SpeechConfig(
                voice_config=gtypes.VoiceConfig(
                    prebuilt_voice_config=gtypes.PrebuiltVoiceConfig(voice_name=self.voice)
                )
            ),
            system_instruction=system_prompt,
            tools=tools,
            # NOTE: Do NOT set thinking_config on native-audio models — budget=0
            # causes the model to return empty responses (no audio, no text).
            # Thought parts are already filtered out in _receive_loop.
            #
            # VAD: HIGH start sensitivity so ZENO catches speech quickly.
            # 800ms silence signals end of user's turn.
            realtime_input_config=gtypes.RealtimeInputConfig(
                automatic_activity_detection=gtypes.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=gtypes.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=gtypes.EndSensitivity.END_SENSITIVITY_LOW,
                    silence_duration_ms=800,
                )
            ),
        )

        async with client.aio.live.connect(
            model=self.model, config=live_config
        ) as session:
            log.info("Gemini Live WebSocket connected.")
            print("[ZENO] ✅ Live session connected. Listening...", flush=True)
            broadcast_state("listening")

            # Run mic → Gemini and Gemini → speaker concurrently
            await asyncio.gather(
                self._send_audio_loop(session),
                self._receive_loop(session),
            )

    async def _build_system_prompt(self) -> str:
        """Build system prompt with injected memory."""
        base = _ZENO_LIVE_SYSTEM_PROMPT
        try:
            from zeno.ai.memory import format_memory_injection
            return format_memory_injection(base)
        except Exception:
            return base

    async def _send_audio_loop(self, session: Any) -> None:
        """Capture microphone audio and stream it to Gemini."""
        from zeno.voice.capture import MicrophoneStream

        mic = MicrophoneStream()
        mic.start()
        audio_queue = mic.subscribe()
        dev_idx = mic._stream.device if mic._stream else "default"
        log.info("Microphone streaming to Gemini Live (device=%s)...", dev_idx)

        try:
            while not self._stop.is_set():
                try:
                    # Get ~80ms audio frame (float32 at 16kHz)
                    frame: np.ndarray = await asyncio.to_thread(
                        audio_queue.get, True, 0.5
                    )
                    # Apply software gain so quiet mics pass VAD (default 6x boost)
                    _gain = float(os.environ.get("ZENO_MIC_GAIN", "6.0"))
                    frame_boosted = np.clip(frame * _gain, -1.0, 1.0)
                    pcm_int16 = (frame_boosted * 32767).astype(np.int16)
                    pcm_bytes = pcm_int16.tobytes()

                    # Use media= (not audio=) — per SDK example for raw PCM blobs
                    await session.send_realtime_input(
                        media=gtypes.Blob(
                            data=pcm_bytes,
                            mime_type="audio/pcm;rate=16000",
                        )
                    )
                except queue.Empty:
                    continue
                except Exception as e:
                    err_str = str(e)
                    # 1000 = Normal closure — server closed session gracefully
                    if "1000" in err_str:
                        log.debug("Audio send: session closed normally.")
                    else:
                        log.warning("Audio send error: %s", e)
                    break
        finally:
            mic.stop()

    async def _receive_loop(self, session: Any) -> None:
        """Receive audio/text/function calls from Gemini and handle them."""
        import sounddevice as sd

        SAMPLE_RATE = 24000  # Gemini Live native-audio outputs at 24kHz
        audio_buffer = bytearray()

        async for response in session.receive():
            if self._stop.is_set():
                break

            # ── server_content: audio / text parts ───────────────────
            sc = response.server_content
            if sc and sc.model_turn and sc.model_turn.parts:
                for part in sc.model_turn.parts:
                    # Skip thought/reasoning parts (no playable content)
                    if getattr(part, "thought", False):
                        continue

                    # Audio chunk — inline_data from native-audio model
                    if part.inline_data and part.inline_data.data:
                        broadcast_state("speaking")
                        audio_buffer.extend(part.inline_data.data)
                        # Play in 100 ms chunks to avoid choppy output
                        if len(audio_buffer) >= SAMPLE_RATE * 2 * 0.1:
                            pcm = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
                            sd.play(pcm.astype(np.float32) / 32768.0,
                                    samplerate=SAMPLE_RATE, blocking=False)
                            audio_buffer.clear()

                    # Text transcript — log and display, do NOT call response.text
                    if part.text:
                        log.debug("Gemini: %s", part.text)
                        print(f"[ZENO] 💬 {part.text}", flush=True)

            # ── tool_call: function invocations ──────────────────────
            if response.tool_call:
                broadcast_state("thinking")
                for fn_call in response.tool_call.function_calls:
                    tool_name = fn_call.name
                    args = dict(fn_call.args) if fn_call.args else {}
                    call_id = fn_call.id

                    log.info("Tool call: %s(%s)", tool_name, args)
                    print(f"[ZENO] 🔧 {tool_name}({args})", flush=True)

                    result_str = await asyncio.to_thread(_call_tool, tool_name, args)
                    log.info("Tool result: %s → %s", tool_name, result_str[:100])

                    await session.send_tool_response(
                        function_responses=gtypes.FunctionResponse(
                            id=call_id,
                            name=tool_name,
                            response={"result": result_str},
                        )
                    )

            # ── turn_complete: flush remaining audio ─────────────────
            if sc and getattr(sc, "turn_complete", False):
                if audio_buffer:
                    pcm = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
                    sd.play(pcm.astype(np.float32) / 32768.0,
                            samplerate=SAMPLE_RATE, blocking=False)
                    audio_buffer.clear()
                broadcast_state("listening")
                asyncio.create_task(self._extract_memories_background())


    async def _extract_memories_background(self) -> None:
        """Post-turn: asynchronously extract memories from recent dialogue."""
        try:
            from zeno.ai.memory import trigger_memory_extraction
            await asyncio.to_thread(trigger_memory_extraction)
        except Exception as e:
            log.debug("Memory extraction skipped: %s", e)

    def stop(self) -> None:
        self._stop.set()
        try:
            broadcast_state("idle")
        except Exception:
            pass
