import re
from typing import List

# Common conjunctions used to join multiple intents in a single utterance
CONJUNCTIONS = [r"\band\b", r"\bthen\b", r"\balso\b", r"\bas well as\b"]
SPLIT_PATTERN = "|".join(CONJUNCTIONS)

def split_utterance(text: str) -> List[str]:
    """
    Split a multi-intent utterance into individual command strings.
    Example: "add a task and remind me in 5 minutes" -> ["add a task", "remind me in 5 minutes"]
    """
    if not text:
        return []
    
    # Split by conjunctions, but keep parts that aren't empty
    parts = re.split(SPLIT_PATTERN, text, flags=re.IGNORECASE)
    
    # Clean up whitespace and filter out empty strings
    cleaned_parts = [p.strip() for p in parts if p.strip()]
    
    # If the split results in nothing (e.g., just conjunctions), return the original text
    return cleaned_parts if cleaned_parts else [text.strip()]
