import json
import urllib.request


def ollama_chat(
    messages: list[dict],
    json_mode: bool = True,
    model: str = "qwen2.5:3b",
    temperature: float = 0.0,
    seed: int | None = None,
) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if json_mode:
        payload["format"] = "json"
    if seed is not None:
        payload["options"]["seed"] = seed

    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return {
        "content": data["message"]["content"],
        "prompt_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": data.get("eval_count", 0),
    }