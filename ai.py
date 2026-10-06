import json
import time
import urllib.error
import urllib.request
from typing import Any

from config import API_KEY, API_TIMEOUT, API_URL, MAX_RETRIES, MAX_TOOL_ROUNDS, MODEL, SYSTEM_PROMPT
from history import get_messages, add_message
from logger import logger
from memory import format_memory
from tools import SCHEMAS, execute


class AIError(RuntimeError):
    pass


def _request(payload: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        raise AIError("OPENAI_API_KEY bulunamadı. .env veya ortam değişkenini ayarla.")

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        method="POST",
    )

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            last_error = AIError(f"API HTTP {exc.code}: {raw[:500]}")
            if exc.code not in {408, 409, 429, 500, 502, 503, 504}:
                raise last_error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = AIError(f"API bağlantı hatası: {exc}")
        time.sleep(2 ** attempt)
    raise last_error or AIError("API isteği başarısız oldu.")


def _output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    parts = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    parts.append(content.get("text", ""))
    return "\n".join(p for p in parts if p).strip()


def _function_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in response.get("output", []) if item.get("type") == "function_call"]


def ask_ai(user_text: str) -> str:
    memory_context = format_memory()
    input_items: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nKalıcı hafıza:\n" + memory_context}
    ]
    input_items.extend(get_messages())
    input_items.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        payload = {
            "model": MODEL,
            "input": input_items,
            "tools": SCHEMAS,
            "tool_choice": "auto",
            "store": False,
        }
        response = _request(payload)
        calls = _function_calls(response)

        if not calls:
            answer = _output_text(response) or "Üzgünüm, cevap üretemedim."
            add_message("user", user_text)
            add_message("assistant", answer)
            return answer

        # Responses API returns output items; feed the model's tool-call items back
        # together with function_call_output items on the next turn.
        input_items.extend(response.get("output", []))
        for call in calls:
            try:
                args = json.loads(call.get("arguments", "{}"))
                result = execute(call["name"], args)
                output = json.dumps(result, ensure_ascii=False)
            except Exception as exc:
                logger.exception("Tool %s failed", call.get("name"))
                output = json.dumps({"error": str(exc)}, ensure_ascii=False)
            input_items.append({
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": output,
            })

    raise AIError("ARIA çok fazla araç çağrısı yaptı; işlem güvenlik nedeniyle durduruldu.")
