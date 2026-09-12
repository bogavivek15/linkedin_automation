"""Shared Gemini client factory. Agents never invent facts when the key is missing."""

from __future__ import annotations

import logging
from typing import Any

from apps.api.app.core.config import settings

logger = logging.getLogger("careeros.gemini")

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]


def gemini_available() -> bool:
    return bool(genai) and bool(str(settings.gemini_api_key or "").strip())


def get_gemini_client() -> Any | None:
    if not gemini_available():
        return None
    return genai.Client(api_key=settings.gemini_api_key)
