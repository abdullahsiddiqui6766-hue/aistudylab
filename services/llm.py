"""
services/llm.py

Central place for talking to Groq. Every other service goes through
`chat_completion()` so error handling, retries, and the API key lookup only
live in one place.

The API key is NEVER hard-coded. It is read from st.secrets["GROQ_API_KEY"]
first, falling back to the GROQ_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import List, Optional

import streamlit as st

DEFAULT_MODEL = "openai/gpt-oss-120b"  # Groq's current general-purpose model.
# NOTE: Groq periodically deprecates/renames models. If this model stops
# working, check https://console.groq.com/docs/models and set a different
# model in .streamlit/secrets.toml under GROQ_MODEL.


class LLMError(Exception):
    """Raised for any Groq API problem; caught by the UI layer and shown as
    a friendly message instead of a stack trace."""


def get_api_key() -> Optional[str]:
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY")


def get_model_name() -> str:
    try:
        if "GROQ_MODEL" in st.secrets:
            return st.secrets["GROQ_MODEL"]
    except Exception:
        pass
    return os.environ.get("GROQ_MODEL", DEFAULT_MODEL)


@st.cache_resource(show_spinner=False)
def _get_client(api_key: str):
    from groq import Groq

    return Groq(api_key=api_key)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    json_mode: bool = False,
) -> str:
    api_key = get_api_key()
    if not api_key:
        raise LLMError(
            "No Groq API key was found. Add GROQ_API_KEY to "
            ".streamlit/secrets.toml (or as an environment variable) to use "
            "the AI features."
        )

    client = _get_client(api_key)
    model = get_model_name()

    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # groq SDK raises various APIStatusError subtypes
        message = str(exc)
        if "rate limit" in message.lower() or "429" in message:
            raise LLMError(
                "The AI service is rate-limited right now. Please wait a "
                "moment and try again."
            ) from exc
        if "401" in message or "authentication" in message.lower():
            raise LLMError(
                "The Groq API key appears to be invalid. Please check your "
                "secrets configuration."
            ) from exc
        raise LLMError(f"The AI service could not complete this request ({message}).") from exc

    try:
        content = response.choices[0].message.content
    except Exception as exc:
        raise LLMError("The AI service returned an unexpected response.") from exc

    return content or ""
