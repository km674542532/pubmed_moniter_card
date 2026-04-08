"""Provider-agnostic LLM client wrapper."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from app.integrations.llm.schemas import LlmClientResponse, LlmHealthcheckResult


class LlmClientError(RuntimeError):
    """Raised when LLM integration call fails."""


@dataclass(slots=True)
class LlmClientConfig:
    provider: str
    model: str
    base_url: str
    api_key: str | None = None
    timeout: int = 30


class LlmClient:
    """Minimal JSON chat wrapper; transport details stay inside integration."""

    def __init__(self, config: LlmClientConfig):
        self.config = config

    def chat_json(self, prompt: str, temperature: float = 0.2) -> LlmClientResponse:
        body = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        req = urllib.request.Request(self.config.base_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = self._extract_json_content(payload)
            return LlmClientResponse(success=True, content=content, raw_response=payload)
        except Exception as exc:
            return LlmClientResponse(success=False, content=None, raw_response=None, error_message=str(exc))

    def healthcheck(self) -> LlmHealthcheckResult:
        result = self.chat_json("Return JSON: {\"ok\": true}", temperature=0)
        if not result.success:
            return LlmHealthcheckResult(
                ok=False,
                provider=self.config.provider,
                model=self.config.model,
                message=f"healthcheck failed: {result.error_message}",
            )
        return LlmHealthcheckResult(
            ok=True,
            provider=self.config.provider,
            model=self.config.model,
            message="ok",
        )

    @staticmethod
    def _extract_json_content(payload: dict) -> dict:
        try:
            content = payload["choices"][0]["message"]["content"]
            if isinstance(content, dict):
                return content
            if isinstance(content, str):
                return json.loads(content)
        except Exception as exc:
            raise LlmClientError(f"LLM returned invalid JSON payload: {exc}") from exc
        raise LlmClientError("LLM returned empty content")
