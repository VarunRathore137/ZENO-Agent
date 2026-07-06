import os
import json
import sys
from typing import Any, Dict, Optional
from zeno.nlp.intent_schema import ParsedIntent

class GeminiClient:
    """
    Client for Gemini Flash 1.5 fallback parsing and web-grounded queries.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._client = None
        self.model_name = "gemini-1.5-flash"

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(api_key=self.api_key)
                self._types = types
            except ImportError:
                print("Error: google-genai package not installed.", file=sys.stderr)
                raise
        return self._client

    def generate_intent(self, transcript: str, context: Optional[str] = None) -> Optional[ParsedIntent]:
        """
        Use Gemini to parse a transcript into a structured intent JSON.
        Includes web grounding for up-to-date info.
        """
        client = self._get_client()
        
        prompt = f"""
        You are the NLP engine for ZENO, a personal AI assistant.
        Parse the following user transcript into a structured JSON intent object.
        
        User Transcript: "{transcript}"
        {f"Context: {context}" if context else ""}
        
        Available Intent Categories and Names (refer to ZENO documentation for full list):
        - task_management: add_task, query_tasks, complete_task, update_task, defer_task, flag_blocker
        - day_planning: start_day_planning, assign_time_block, query_schedule
        - session_control: initiate_shutdown, deliver_briefing
        - project_planning: start_rubber_duck, generate_prd
        - workspace_control: activate_workspace, enable_focus_mode
        
        Return ONLY a JSON object with this schema:
        {{
            "intent_category": "string",
            "intent_name": "string",
            "slots": {{ "key": "value" }},
            "confidence": float (0.0 to 1.0)
        }}
        
        If you need to search the web for up-to-date information to fulfill the request, do so.
        """
        
        try:
            # Enable Google Search grounding
            config = self._types.GenerateContentConfig(
                tools=[self._types.Tool(google_search=self._types.GoogleSearch())],
                response_mime_type="application/json"
            )
            
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            # The SDK might return the JSON string directly in the text
            result = json.loads(response.text)
            
            return ParsedIntent(
                intent_category=result.get("intent_category", "unknown"),
                intent_name=result.get("intent_name", "unknown"),
                slots=result.get("slots", {}),
                confidence=result.get("confidence", 0.0),
                raw_transcript=transcript
            )
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            return None

def get_gemini_client() -> GeminiClient:
    return GeminiClient()
