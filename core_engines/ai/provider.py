"""
AI Provider abstraction layer.

Supports multiple backends without breaking the system.
Local fallback when AI is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rastro.ai.provider")


class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class OllamaProvider(AIProvider):
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self._available: Optional[bool] = None

    def _check(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check()
        return self._available

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        prompt = self._format_prompt(messages)
        try:
            import urllib.request
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            }).encode()
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                return result.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            self._available = False
            return ""

    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant: ")
        return "\n".join(parts)


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        if not self.api_key:
            return ""
        try:
            import urllib.request
            payload = json.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }).encode()
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"OpenAI-compatible call failed: {e}")
            return ""


class LocalFallbackProvider(AIProvider):
    """Rule-based fallback that works without any LLM."""

    @property
    def name(self) -> str:
        return "local/rule-based"

    def is_available(self) -> bool:
        return True

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        last = messages[-1]["content"] if messages else ""
        last_lower = last.lower()

        if "hola" in last_lower or "hello" in last_lower or "qué tal" in last_lower:
            return "Estoy listo para analizar tu ecosistema. Pregúntame sobre targets, oportunidades, o qué hacer ahora."
        if "quiénes soy" in last_lower or "qué eres" in last_lower:
            return (
                "Soy Rastro AI, el analista principal del sistema. "
                "Analizo datos reales de targets, endpoints, findings, "
                "veredictos y programas para darte recomendaciones accionables."
            )
        return (
            "No tengo conexión con un modelo de lenguaje en este momento. "
            "Mis recomendaciones basadas en reglas internas siguen disponibles "
            "en la sección Insights y Recommendations del panel."
        )


def get_provider() -> AIProvider:
    provider_type = os.environ.get("AI_PROVIDER", "ollama").lower()

    if provider_type == "openai":
        provider: AIProvider = OpenAICompatibleProvider()
        if provider.is_available():
            return provider

    if provider_type == "ollama":
        provider = OllamaProvider()
        if provider.is_available():
            return provider

    provider = OpenAICompatibleProvider()
    if provider.is_available():
        return provider

    provider = OllamaProvider()
    if provider.is_available():
        return provider

    logger.info("No LLM provider available — using local rule-based fallback")
    return LocalFallbackProvider()
