import os
import requests
from typing import Optional

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Vision + text; efficient on OpenRouter free tier. Good for drawing analysis and SOR text.
DEFAULT_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"
FALLBACK_MODEL = "google/gemma-4-31b-it:free"


def get_model() -> str:
    return os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)


def chat(
    prompt: str,
    *,
    model: Optional[str] = None,
    system: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY not set in environment")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model or get_model(),
        "messages": messages,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if response.status_code != 200:
        if payload["model"] != FALLBACK_MODEL:
            return chat(
                prompt,
                model=FALLBACK_MODEL,
                system=system,
                max_tokens=max_tokens,
            )
        response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"].get("content")
    if not content:
        raise ValueError("Empty response from OpenRouter")
    return content.strip()
