"""Feishu webhook client with unified error handling and retries."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

from app.integrations.feishu.schemas import FeishuDeliveryResult


@dataclass(slots=True)
class FeishuClientConfig:
    webhook_url: str
    timeout: int = 15
    max_retries: int = 2
    retry_interval_seconds: float = 0.5


class FeishuClient:
    def __init__(self, config: FeishuClientConfig):
        self.config = config

    def send_card(self, payload: dict) -> FeishuDeliveryResult:
        return self._post(payload)

    def update_card(self, card_id: str, payload: dict) -> FeishuDeliveryResult:
        # 预留：当前 webhook 版本通常不支持 update；保留接口以便后续使用开放平台 API。
        merged = dict(payload)
        merged["card_id"] = card_id
        return self._post(merged)

    def _post(self, payload: dict) -> FeishuDeliveryResult:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_error: str | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                ok = int(body.get("code", 0)) == 0
                card_id = body.get("data", {}).get("message_id") if isinstance(body.get("data"), dict) else None
                if ok:
                    return FeishuDeliveryResult(success=True, card_id=card_id, raw_response=body)
                last_error = body.get("msg", "feishu send failed")
            except Exception as exc:
                last_error = str(exc)

            if attempt < self.config.max_retries:
                time.sleep(self.config.retry_interval_seconds)

        return FeishuDeliveryResult(success=False, card_id=None, raw_response=None, error_message=last_error)
