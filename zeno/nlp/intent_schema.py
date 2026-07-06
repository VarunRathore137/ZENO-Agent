from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ParsedIntent:
    """
    Standardized intent object output by the NLP parser.
    Matches SPEC.md R2 requirements.
    """
    intent_category: str
    intent_name: str
    slots: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_transcript: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert the intent to a JSON-serializable dictionary."""
        return {
            "intent_category": self.intent_category,
            "intent_name": self.intent_name,
            "slots": self.slots,
            "confidence": self.confidence,
            "raw_transcript": self.raw_transcript
        }
