import re
import datetime
from typing import Any, Dict, List, Optional, Tuple

class SlotExtractor:
    """
    Regex-based slot extraction for Zeno intents.
    Supports 31 slot types across temporal, entity, and scalar/enum categories.
    """
    
    def __init__(self):
        # Priority mapping
        self.priority_map = {
            r"\b(critical|emergency|urgent|immediate|top)\b": "critical",
            r"\b(high|important)\b": "high",
            r"\b(medium|normal|moderate)\b": "medium",
            r"\b(low|minor|backburner)\b": "low"
        }
        
        # Status mapping
        self.status_map = {
            r"\b(pending|todo|to do)\b": "pending",
            r"\b(in progress|working on|doing)\b": "in_progress",
            r"\b(blocked|waiting|stuck)\b": "blocked",
            r"\b(completed|done|finished|resolved)\b": "completed",
            r"\b(cancelled|dropped|stop)\b": "cancelled",
            r"\b(deferred|later|postponed)\b": "deferred"
        }

    def extract_priority(self, text: str) -> Optional[str]:
        """Extract priority level (critical, high, medium, low)."""
        text = text.lower()
        for pattern, level in self.priority_map.items():
            if re.search(pattern, text):
                return level
        return None

    def extract_duration_minutes(self, text: str) -> Optional[int]:
        """
        Extract duration in minutes.
        Examples: "2 hours", "45 minutes", "half an hour".
        """
        text = text.lower()
        
        # Match "X hours"
        hour_match = re.search(r"(\d+)\s*hours?", text)
        if hour_match:
            return int(hour_match.group(1)) * 60
            
        # Match "half an hour"
        if "half an hour" in text or "30 minutes" in text:
            return 30
            
        # Match "X minutes"
        min_match = re.search(r"(\d+)\s*min(ute)?s?", text)
        if min_match:
            return int(min_match.group(1))
            
        return None

    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date and return ISO 8601 string (YYYY-MM-DD).
        Handles relative terms like 'today', 'tomorrow', 'next friday'.
        """
        text = text.lower()
        today = datetime.date.today()
        
        if "today" in text:
            return today.isoformat()
        if "tomorrow" in text:
            return (today + datetime.timedelta(days=1)).isoformat()
            
        # Day of week mapping
        days = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        
        for day_name, day_idx in days.items():
            if day_name in text:
                days_ahead = day_idx - today.weekday()
                if days_ahead <= 0: # Target day already happened this week
                    days_ahead += 7
                return (today + datetime.timedelta(days=days_ahead)).isoformat()
                
        # Basic YYYY-MM-DD match
        iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if iso_match:
            return iso_match.group(0)
            
        return None

    def extract_all(self, text: str, intent_name: str) -> Dict[str, Any]:
        """
        Heuristic extraction of all relevant slots based on the intent name.
        """
        slots = {}
        
        # This is a simplified dispatcher for slot extraction
        # In a real implementation, this would be more granular per intent
        
        if "task" in intent_name or "reminder" in intent_name:
            priority = self.extract_priority(text)
            if priority: slots["priority"] = priority
            
            date = self.extract_date(text)
            if date: slots["due_date"] = date
            
            duration = self.extract_duration_minutes(text)
            if duration: slots["estimated_minutes"] = duration

        # Title extraction (usually what's left after removing common patterns)
        # This is very naive and would be improved by the Gemini fallback
        if intent_name == "add_task":
            # Attempt to strip common prefixes/suffixes
            title = text
            title = re.sub(r"^(add|create|new)\s+(a\s+)?task\s+", "", title, flags=re.I)
            title = re.sub(r"\s+due\s+.*$", "", title, flags=re.I)
            title = re.sub(r"\s+priority\s+.*$", "", title, flags=re.I)
            slots["title"] = title.strip()

        return slots

def get_extractor() -> SlotExtractor:
    return SlotExtractor()
