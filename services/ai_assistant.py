from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]  
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None


class AIAssistant:
    """
    Wrapper around the OpenAI Chat Completions API, with simple message history.
    Each instance can have its own system prompt (cyber, IT, data science, etc.).
    """

    def __init__(self, system_prompt: str = "You are a helpful assistant."):
        self._system_prompt = system_prompt
        self._history: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt and keep it as the first message."""
        self._system_prompt = prompt
        if self._history and self._history[0]["role"] == "system":
            self._history[0]["content"] = prompt
        else:
            self._history.insert(0, {"role": "system", "content": prompt})

    def send_message(self, user_message: str) -> str:
        """
        Add a user message, call the OpenAI API, store and return the assistant reply.
        If the API key is missing, return a fallback message.
        """
        self._history.append({"role": "user", "content": user_message})

        if client is None:
            fallback = (
                "[AI unavailable: missing OPENAI_API_KEY in .env]\n\n"
                f"(Echo) {user_message[:200]}"
            )
            self._history.append({"role": "assistant", "content": fallback})
            return fallback

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=self._history,
        )

        reply = response.choices[0].message.content
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def clear_history(self) -> None:
        """Clear chat history but keep the system prompt."""
        self._history = [{"role": "system", "content": self._system_prompt}]
