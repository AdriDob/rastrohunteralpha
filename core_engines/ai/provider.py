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
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("rastro.ai.provider")


@dataclass
class ProviderSpec:
    """Describes an available provider type."""
    id: str
    label: str
    models: list[str] = field(default_factory=list)
    env_host: str = ""
    env_model: str = ""
    env_key: str = ""
    default_host: str = ""
    default_model: str = ""


PROVIDER_CATALOG: list[ProviderSpec] = [
    ProviderSpec(
        id="ollama",
        label="Ollama (Local)",
        models=["qwen2.5-coder:7b", "qwen2.5-coder:14b", "codellama:7b", "llama3.1:8b", "mistral:7b"],
        env_host="OLLAMA_HOST",
        env_model="OLLAMA_MODEL",
        default_host="http://localhost:11434",
        default_model="qwen2.5-coder:7b",
    ),
    ProviderSpec(
        id="openai",
        label="OpenAI Compatible",
        models=["gpt-4o-mini", "gpt-4o", "gpt-4", "gpt-3.5-turbo"],
        env_host="OPENAI_BASE_URL",
        env_model="LLM_MODEL",
        env_key="OPENAI_API_KEY",
        default_host="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    ProviderSpec(
        id="local",
        label="Local Rule-Based (No LLM)",
        models=[],
        default_host="",
        default_model="",
    ),
]


class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        ...

    def chat_stream(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        """Override for SSE streaming. Default yields the full response."""
        yield self.chat(messages, max_tokens=max_tokens)

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def get_config(self) -> dict:
        return {"provider": self.name, "available": self.is_available()}


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

    def chat_stream(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        try:
            import urllib.request
            prompt = self._format_prompt(messages)
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {"num_predict": max_tokens, "temperature": 0.3},
            }).encode()
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    chunk = json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except Exception as e:
            logger.warning(f"Ollama stream failed: {e}")
            self._available = False


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

    def chat_stream(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> Generator[str, None, None]:
        if not self.api_key:
            return
        try:
            import urllib.request
            payload = json.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "stream": True,
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
                for line in resp:
                    line = line.decode().strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
        except Exception as e:
            logger.warning(f"OpenAI-compatible stream failed: {e}")

    def get_config(self) -> dict:
        return {
            "provider": self.name,
            "available": self.is_available(),
            "model": self.model,
            "base_url": self.base_url,
        }


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

    def get_config(self) -> dict:
        return {"provider": self.name, "available": True}


class ProviderRegistry:
    """Manages provider lifecycle with DB-persisted config and env fallback."""

    def __init__(self):
        self._current: Optional[AIProvider] = None
        self._loaded = False

    def _load_config(self) -> dict:
        """Load config from DB; fall back to env vars."""
        config = {}
        try:
            from database import db, models
            session = db.SessionLocal()
            try:
                rows = session.query(models.AIProviderConfig).all()
                for row in rows:
                    config[row.key] = row.value
            finally:
                session.close()
        except Exception:
            pass
        config.setdefault("provider_type", os.environ.get("AI_PROVIDER", "ollama"))
        config.setdefault("host", os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
        config.setdefault("model", os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"))
        config.setdefault("api_key", os.environ.get("OPENAI_API_KEY", ""))
        config.setdefault("api_base", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
        config.setdefault("llm_model", os.environ.get("LLM_MODEL", "gpt-4o-mini"))
        return config

    def _save_config(self, cfg: dict):
        try:
            from database import db, models
            session = db.SessionLocal()
            try:
                for key, value in cfg.items():
                    existing = session.query(models.AIProviderConfig).filter(
                        models.AIProviderConfig.key == key
                    ).first()
                    if existing:
                        existing.value = str(value)
                    else:
                        session.add(models.AIProviderConfig(key=key, value=str(value)))
                session.commit()
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Failed to save AI config: {e}")

    def build_provider(self, cfg: dict) -> AIProvider:
        ptype = cfg.get("provider_type", "ollama")
        if ptype == "openai":
            p = OpenAICompatibleProvider(
                api_key=cfg.get("api_key", ""),
                base_url=cfg.get("api_base", "https://api.openai.com/v1"),
                model=cfg.get("llm_model", "gpt-4o-mini"),
            )
            if p.is_available():
                return p
            logger.info("OpenAI provider unavailable, trying Ollama")
        if ptype == "ollama" or True:
            p = OllamaProvider(
                host=cfg.get("host", "http://localhost:11434"),
                model=cfg.get("model", "qwen2.5-coder:7b"),
            )
            if p.is_available():
                return p
            logger.info("Ollama provider unavailable, trying alternatives")
        p = OpenAICompatibleProvider(
            api_key=cfg.get("api_key", ""),
            base_url=cfg.get("api_base", "https://api.openai.com/v1"),
            model=cfg.get("llm_model", "gpt-4o-mini"),
        )
        if p.is_available():
            return p
        p2 = OllamaProvider(
            host=cfg.get("host", "http://localhost:11434"),
            model=cfg.get("model", "qwen2.5-coder:7b"),
        )
        if p2.is_available():
            return p2
        logger.info("No LLM provider available — using local rule-based fallback")
        return LocalFallbackProvider()

    def get_provider(self) -> AIProvider:
        if not self._loaded or self._current is None:
            cfg = self._load_config()
            self._current = self.build_provider(cfg)
            self._loaded = True
        return self._current

    def set_config(self, updates: dict) -> AIProvider:
        cfg = self._load_config()
        cfg.update(updates)
        self._save_config(updates)
        self._current = self.build_provider(cfg)
        return self._current

    def list_providers(self) -> list[dict]:
        result = []
        for spec in PROVIDER_CATALOG:
            current = self.get_provider()
            available = True if spec.id == "local" else None
            if spec.id != "local":
                if spec.id == "ollama":
                    p = OllamaProvider(
                        host=os.environ.get(spec.env_host, spec.default_host),
                    )
                    available = p.is_available()
                elif spec.id == "openai":
                    available = bool(os.environ.get("OPENAI_API_KEY") or
                                     self._load_config().get("api_key"))
            result.append({
                "id": spec.id,
                "label": spec.label,
                "models": spec.models,
                "available": available,
                "active": current.name.startswith(spec.id),
            })
        return result


_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def get_provider() -> AIProvider:
    return get_registry().get_provider()
