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
            "Create a task to review PR 47"
        ],
        "query_tasks": [
            "What are my tasks for today?",
            "Show me everything blocked",
            "What high priority tasks are pending?"
        ],
        "complete_task": [
            "Mark the login bug as done",
            "Complete the unit test task",
            "I finished writing the API docs"
        ],
        "update_task": [
            "Change the deadline on the report to Thursday",
            "Move the API task to high priority"
        ]
    },
    "day_planning": {
        "start_day_planning": [
            "Let's plan my day",
            "I want to build my schedule for today",
            "Help me plan today"
        ],
        "query_schedule": [
            "What's my schedule for today?",
            "When's my next meeting?"
        ]
    },
    "workspace_control": {
        "activate_workspace": [
            "Start dev mode",
            "Switch to writing workspace",
            "Load my design workspace"
        ],
        "enable_focus_mode": [
            "Enable DND",
            "Focus mode for 45 minutes",
            "Don't disturb me for an hour"
        ]
    }
}

CONFIDENCE_THRESHOLD = 0.75

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
        """
        if not text:
            return None
            
        text = text.lower()
        
        # Process uses fuzz.WRatio by default, which is good for varied phrasings
        # We compare against all flattened examples
        best_match = process.extractOne(
            text, 
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
        slots = self.extractor.extract_all(text, name)
        
        return ParsedIntent(
            intent_category=category,
            intent_name=name,
            slots=slots,
            confidence=confidence,
            raw_transcript=text
        )

def get_classifier() -> IntentClassifier:
    return IntentClassifier()
