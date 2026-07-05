import json
import time
import requests
from pydantic import ValidationError

from config import settings
from models import ReelPlan
from creative.prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    DIRECTOR_USER_PROMPT,
    DIRECTOR_REPAIR_PROMPT,
    FALLBACK_QUERY_SYSTEM_PROMPT,
    FALLBACK_QUERY_USER_PROMPT,
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") or part.startswith("["):
                return part
    return text


class CreativeDirector:
    def __init__(self):
        self.backend = settings.LLM_BACKEND

    def generate_plan(self, topic: str, mood: str = "neutral", style_preset: str = "cool-minimal") -> ReelPlan:
        system = DIRECTOR_SYSTEM_PROMPT
        user = DIRECTOR_USER_PROMPT.format(topic=topic, mood=mood, style_preset=style_preset)

        raw = self._call_llm(system, user)
        try:
            return ReelPlan.model_validate_json(_strip_fences(raw))
        except (ValidationError, json.JSONDecodeError) as e:
            print(f"⚠️  Plan validation failed, retrying once with repair prompt: {e}")
            repair_user = DIRECTOR_REPAIR_PROMPT.format(error=str(e), previous_output=raw)
            raw2 = self._call_llm(system, repair_user)
            return ReelPlan.model_validate_json(_strip_fences(raw2))

    def generate_fallback_queries(self, caption: str, visual_description: str, failed_queries: list) -> list:
        user = FALLBACK_QUERY_USER_PROMPT.format(
            caption=caption, visual_description=visual_description, failed_queries=failed_queries
        )
        try:
            raw = self._call_llm(FALLBACK_QUERY_SYSTEM_PROMPT, user)
            queries = json.loads(_strip_fences(raw))
            return [q for q in queries if isinstance(q, str)][:4]
        except Exception as e:
            print(f"   Fallback query generation failed: {e}")
            return []

    def _call_llm(self, system: str, user: str) -> str:
        try:
            return self._dispatch(system, user)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (429, 500, 502, 503, 504):
                backoff = 20 if status == 429 else 2
                print(f"   LLM call failed ({status}), retrying once after {backoff}s backoff...")
                time.sleep(backoff)
                return self._dispatch(system, user)
            raise

    def _dispatch(self, system: str, user: str) -> str:
        if self.backend == "gemini":
            return self._call_gemini(system, user)
        elif self.backend == "anthropic":
            return self._call_anthropic(system, user)
        elif self.backend == "openai":
            return self._call_openai(system, user)
        raise ValueError(f"Unknown LLM_BACKEND: {self.backend}")

    def _call_gemini(self, system: str, user: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": user}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_anthropic(self, system: str, user: str) -> str:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    def _call_openai(self, system: str, user: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        r = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content


if __name__ == "__main__":
    director = CreativeDirector()
    plan = director.generate_plan("Hidden cafes in Tokyo's backstreets")
    print(plan.model_dump_json(indent=2))
