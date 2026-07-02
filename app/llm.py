"""LLM interaction with Google Gemini."""

import os
import json
import re
import time
import logging
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class LLM:
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 10, 20]  # seconds

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    def generate(
        self, system_prompt: str, user_message: str, temperature: float = 0.7
    ) -> str:
        """Generate response from Gemini with retry on transient errors."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature,
                        max_output_tokens=2048,
                    ),
                )
                return response.text
            except Exception as e:
                last_error = e
                err_str = str(e)
                # Retry on 429 (rate limit) or 503 (service unavailable)
                if "429" in err_str or "503" in err_str or "UNAVAILABLE" in err_str:
                    delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                    logger.warning(f"Retryable error (attempt {attempt+1}/{self.MAX_RETRIES}), waiting {delay}s: {err_str[:100]}")
                    time.sleep(delay)
                else:
                    break  # Non-retryable error
        raise RuntimeError(f"LLM generation failed: {str(last_error)}")

    def extract_json(self, text: str) -> list[dict]:
        """Extract JSON array from LLM response."""
        try:
            # Try to find JSON array in response
            match = re.search(r'\[.*?\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass
        return []

    def format_conversation(self, messages: list[dict]) -> str:
        """Format conversation history for prompt."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def format_assessments(self, assessments: list) -> str:
        """Format assessments for LLM context."""
        if not assessments:
            return "No assessments available."

        lines = []
        for i, a in enumerate(assessments, 1):
            parts = [f"{i}. {a.name}"]
            parts.append(f"   URL: {a.url}")
            parts.append(f"   Test Type: {a.test_type}")
            parts.append(f"   Keys: {', '.join(a.keys)}")
            if a.duration:
                parts.append(f"   Duration: {a.duration}")
            if a.languages:
                langs = a.languages[:5]
                lang_str = ", ".join(langs)
                if len(a.languages) > 5:
                    lang_str += f" (+{len(a.languages) - 5} more)"
                parts.append(f"   Languages: {lang_str}")
            if a.job_levels:
                parts.append(f"   Job Levels: {', '.join(a.job_levels)}")
            if a.description:
                desc = a.description[:200]
                parts.append(f"   Description: {desc}")
            lines.append("\n".join(parts))
        return "\n\n".join(lines)
