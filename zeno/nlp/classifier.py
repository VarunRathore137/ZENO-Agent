import sys
from typing import Dict, List, Optional, Tuple
from rapidfuzz import process, fuzz
from .intent_schema import ParsedIntent
from .slots import get_extractor

# Mapping of intent_category -> intent_name -> example_utterances
INTENT_EXAMPLES = {
    "task_management": {
        "add_task": [
            "Add task fix the login bug",
            "New task: write unit tests",
            "Create a task to review PR 47",
            "Add task write unit tests",
            "Create task deploy to staging",
            "Make a task to refactor the auth module",
            "Add a task for code review",
            "New task update the readme",
            "Please create a task for completing the report",
            "Please add a task to review the pull request",
            "Can you add a task to fix the build",
            "I need to add a task for writing tests",
            "Create a task for finishing the project today",
            "Add a new task to update the documentation",
        ],
        "query_tasks": [
            "What are my tasks for today?",
            "Show me everything blocked",
            "What high priority tasks are pending?",
            "List my tasks",
            "What do I have to do today?",
        ],
        "complete_task": [
            "Mark the login bug as done",
            "Complete the unit test task",
            "I finished writing the API docs",
            "Done with the PR review",
            "Task complete: deploy to staging",
        ],
        "update_task": [
            "Change the deadline on the report to Thursday",
            "Move the API task to high priority",
        ]
    },
    "day_planning": {
        "start_day_planning": [
            "Let's plan my day",
            "I want to build my schedule for today",
            "Help me plan today",
        ],
        "query_schedule": [
            "What's my schedule for today?",
            "When's my next meeting?",
        ]
    },
    "workspace_control": {
        "activate_workspace": [
            "Start dev mode",
            "Switch to writing workspace",
            "Load my design workspace",
            "Set up workspace",
        ],
        "enable_focus_mode": [
            "Enable DND",
            "Focus mode for 45 minutes",
            "Don't disturb me for an hour",
        ],
        "setup_workspace": [
            "Set up my coding workspace",
            "Launch dev workspace",
            "Open my workspace",
        ],
        "list_workspaces": [
            "Show my workspaces",
            "What workspaces do I have?",
        ],
    },

    # ── OS Agent intents (desktop control) ────────────────────────────────────
    "os_control": {
        "open_app": [
            "Open Chrome",
            "Launch VS Code",
            "Open Spotify",
            "Start the terminal",
            "Open File Explorer",
            "Launch Calculator",
            "Open Discord",
            "Start VS Code",
            "Open Notepad",
            "Launch Edge",
        ],
        "close_app": [
            "Close Chrome",
            "Kill VS Code",
            "Close Spotify",
            "Quit the terminal",
        ],
        "open_website": [
            "Open YouTube",
            "Go to GitHub",
            "Open Gmail",
            "Navigate to Stack Overflow",
            "Open Reddit",
            "Go to Google",
        ],
        "search_web": [
            "Search the web for Python async tips",
            "Look up React hooks tutorial",
            "Search for machine learning papers",
            "Find information about FastAPI",
        ],
        "search_youtube": [
            "Search YouTube for Lo-fi music",
            "Find on YouTube: Python tutorial",
            "YouTube search: system design interview",
        ],
        "take_screenshot": [
            "Take a screenshot",
            "Capture the screen",
            "Screenshot please",
            "Snap a screenshot",
        ],
        "read_screen": [
            "Read my screen",
            "What's on my screen?",
            "Read what's on screen",
            "OCR my screen",
            "What does the screen say?",
        ],
        "set_volume": [
            "Set volume to 50",
            "Volume at 80 percent",
            "Turn volume to 30",
        ],
        "volume_up": [
            "Volume up",
            "Turn it up",
            "Increase volume",
            "Make it louder",
        ],
        "volume_down": [
            "Volume down",
            "Turn it down",
            "Lower the volume",
            "Make it quieter",
        ],
        "mute_toggle": [
            "Mute",
            "Unmute",
            "Toggle mute",
            "Mute the audio",
        ],
        "get_system_info": [
            "System info",
            "How's my CPU?",
            "Check RAM usage",
            "How much memory am I using?",
            "What's my disk space?",
        ],
        "get_weather": [
            "What's the weather?",
            "How's the weather today?",
            "Is it going to rain?",
            "Weather in Mumbai",
            "Current temperature",
        ],
        "get_news": [
            "What's in the news?",
            "Give me today's news",
            "Tech news",
            "Latest technology news",
            "Show me the headlines",
        ],
        "run_terminal": [
            "Run command ls",
            "Execute git status",
            "Terminal command: pip install requests",
            "Run in terminal: npm start",
        ],
        "get_clipboard": [
            "What's in my clipboard?",
            "Read clipboard",
            "Show clipboard contents",
        ],
        "check_calendar": [
            "What's on my calendar?",
            "Any meetings today?",
            "Check my schedule",
            "What events do I have this week?",
        ],
        "check_email": [
            "Check my email",
            "Any new emails?",
            "Read my Gmail",
            "What emails do I have?",
        ],
        "send_email": [
            "Send an email to John",
            "Email Sarah about the project",
            "Draft an email to the team",
        ],
        "minimize_window": [
            "Minimize Chrome",
            "Hide the window",
            "Minimize VS Code",
        ],
        "maximize_window": [
            "Maximize the window",
            "Full screen VS Code",
            "Make Chrome bigger",
        ],
    },

    "notes": {
        "capture_idea": [
            "Note: the API should use pagination",
            "Save this idea: use Redis for caching",
            "Brain dump: need to refactor auth module",
            "Quick note about the bug I found",
            "Jot this down",
        ],
        "search_notes": [
            "Search my notes for Redis",
            "Find my note about authentication",
            "Look up notes on API design",
        ],
    },

    "reminders": {
        "set_reminder": [
            "Remind me in 30 minutes to take a break",
            "Set a reminder for the standup at 10am",
            "Alert me in an hour",
            "Remind me to push code at 6pm",
        ],
        "list_reminders": [
            "What reminders do I have?",
            "Show my reminders",
            "List active reminders",
        ],
    },

    "session_control": {
        "start_new_session": [
            "Start my work session",
            "Begin a new session",
            "I'm starting work",
        ],
        "initiate_shutdown": [
            "Shut down ZENO",
            "End the session",
            "I'm done for today",
            "Shut down",
            "Goodbye ZENO",
        ],
    },
}

# Threshold: "tell me a joke" scored 85.5% -> add_task (wrong).
# 0.86 cleanly rejects that while still accepting clear matches.
CONFIDENCE_THRESHOLD = 0.86

# These WHOLE-WORD tokens signal a clearly conversational request.
# Only match when none of the task keywords (task, reminder, note, schedule,
# meeting, workspace, focus) appear in the same sentence.
# Simple check: if the sentence contains a task keyword, let the classifier decide.
TASK_KEYWORDS = {
    "task", "tasks", "reminder", "reminders", "note", "notes",
    "schedule", "meeting", "workspace", "focus", "priority", "deadline",
    "session", "plan", "planning", "todo",
}
CONVERSATIONAL_TRIGGERS = {
    "joke", "funny", "laugh", "humor", "prank",
    "hello", "hi there", "how are you", "how's it going", "what's up",
    "weather", "news", "who is", "who was", "when did",
    "explain", "tell me about", "describe", "what does",
    "thank", "thanks", "cool", "awesome", "nice job",
    "good morning", "good evening", "good night",
}

class IntentClassifier:
    """
    Fuzzy-matching based intent classifier using RapidFuzz.
    """
    def __init__(self):
        self.extractor = get_extractor()
        # Flatten examples for easier processing: (utterance, (category, name))
        self.flattened_examples: List[Tuple[str, Tuple[str, str]]] = []
        for cat, intents in INTENT_EXAMPLES.items():
            for name, examples in intents.items():
                for ex in examples:
                    self.flattened_examples.append((ex.lower(), (cat, name)))

    def classify(self, text: str) -> Optional[ParsedIntent]:
        """
        Classify the text into an intent.
        Returns a ParsedIntent if confidence >= threshold, else None.
        Routes to Gemini fallback (None) if the text looks conversational.
        """
        if not text:
            return None

        text_lower = text.lower()

        # Conversational bypass: route to Gemini when the user is clearly chatting
        # and no task-related keyword anchors the sentence.
        # E.g. "tell me a joke" -> Gemini, but "show my tasks" -> classifier.
        words = set(text_lower.split())
        has_task_context = bool(words & TASK_KEYWORDS)
        if not has_task_context:
            for trigger in CONVERSATIONAL_TRIGGERS:
                if trigger in text_lower:
                    return None

        # Process uses fuzz.WRatio by default, which is good for varied phrasings
        # We compare against all flattened examples
        best_match = process.extractOne(
            text_lower,
            [ex[0] for ex in self.flattened_examples],
            scorer=fuzz.WRatio
        )

        if not best_match:
            return None

        matched_text, score, index = best_match
        confidence = score / 100.0

        if confidence < CONFIDENCE_THRESHOLD:
            return None

        # Retrieve category and name
        category, name = self.flattened_examples[index][1]

        # Extract slots
        slots = self.extractor.extract_all(text_lower, name)

        return ParsedIntent(
            intent_category=category,
            intent_name=name,
            slots=slots,
            confidence=confidence,
            raw_transcript=text
        )

def get_classifier() -> IntentClassifier:
    return IntentClassifier()
