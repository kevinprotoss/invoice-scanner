import json
import time
from datetime import datetime, timezone

from anthropic import Anthropic

from ..config import settings
from ..models.invoice import ClaudeInvoicePayload
from .prompt import SYSTEM_PROMPT, build_user_prompt


class LlmError(Exception):
    def __init__(
        self,
        message: str,
        raw_text: str | None = None,
        stop_reason: str | None = None,
    ):
        super().__init__(message)
        self.raw_text = raw_text
        self.stop_reason = stop_reason


def _get_client() -> Anthropic:
    if not settings.anthropic_api_key:
        raise LlmError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=settings.anthropic_api_key)


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts)


def _strict_json(text: str) -> dict:
    stripped = text.strip()
    if not stripped:
        raise LlmError("empty response", raw_text=text)
    if stripped.startswith("```"):
        raise LlmError(
            "response wrapped in markdown code fence",
            raw_text=text,
        )
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        raise LlmError(
            f"invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})",
            raw_text=text,
        )


def analyze(ocr_data: dict) -> tuple[ClaudeInvoicePayload, str, dict]:
    """Synchronous Claude call.

    Returns (payload, raw_text, meta_dict).
    Raises LlmError on any failure. raw_text is preserved for debugging.
    """
    client = _get_client()
    ocr_text = json.dumps(ocr_data, ensure_ascii=False, indent=2)

    started = time.monotonic()
    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(ocr_text)}],
        )
    except Exception as e:
        raise LlmError(f"anthropic call failed: {type(e).__name__}: {e}") from e
    elapsed = round(time.monotonic() - started, 3)

    raw_text = _extract_text(response)
    stop_reason = response.stop_reason

    if stop_reason != "end_turn":
        raise LlmError(
            f"unexpected stop_reason: {stop_reason}",
            raw_text=raw_text,
            stop_reason=stop_reason,
        )

    parsed = _strict_json(raw_text)

    try:
        payload = ClaudeInvoicePayload.model_validate(parsed)
    except Exception as e:
        raise LlmError(
            f"schema validation failed: {e}",
            raw_text=raw_text,
        )

    meta = {
        "model": response.model,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": stop_reason,
        "processing_time_seconds": elapsed,
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return payload, raw_text, meta