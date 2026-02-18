"""
LLM Client Abstraction — unified interface for Ollama, Anthropic, and OpenAI.

Default: Ollama (free, local). Falls back through provider chain on failure.
"""

import json
import logging
import time
from typing import Optional

import httpx

from backend.config.settings import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds


class LLMError(Exception):
    pass


class LLMClient:
    """Unified LLM interface with retry + fallback chain."""

    def __init__(self):
        self._provider = settings.llm_provider
        self._fallback_chain = self._build_fallback_chain()

    def _build_fallback_chain(self) -> list[str]:
        chain = [self._provider]
        for p in ("ollama", "anthropic", "openai"):
            if p not in chain and self._is_provider_configured(p):
                chain.append(p)
        return chain

    def _is_provider_configured(self, provider: str) -> bool:
        if provider == "ollama":
            return True
        if provider == "anthropic":
            return bool(settings.anthropic_api_key)
        if provider == "openai":
            return bool(settings.openai_api_key)
        return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        last_error = None
        for provider in self._fallback_chain:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    result = self._call_provider(provider, prompt, system_prompt)
                    logger.info(f"LLM response from {provider} ({len(result)} chars)")
                    return result
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"LLM call failed ({provider}, attempt {attempt + 1}): {e}"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
            logger.error(f"All retries exhausted for provider: {provider}")

        raise LLMError(f"All LLM providers failed. Last error: {last_error}")

    @property
    def active_provider(self) -> str:
        return self._provider

    def _call_provider(self, provider: str, prompt: str, system_prompt: str) -> str:
        if provider == "ollama":
            return self._call_ollama(prompt, system_prompt)
        elif provider == "anthropic":
            return self._call_anthropic(prompt, system_prompt)
        elif provider == "openai":
            return self._call_openai(prompt, system_prompt)
        raise LLMError(f"Unknown provider: {provider}")

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        url = f"{settings.ollama_base_url}/api/generate"
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 4096},
        }
        if system_prompt:
            payload["system"] = system_prompt

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["response"]

    def _call_anthropic(self, prompt: str, system_prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 4096,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def _call_openai(self, prompt: str, system_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# Module-level singleton
llm_client = LLMClient()
