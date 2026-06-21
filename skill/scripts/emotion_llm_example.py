#!/usr/bin/env python3
"""Example LLM emotion command for OpenTSC's `llm` / `hybrid` emotion backend.

Contract (see opentsc_core/emotion.py):
    stdin  : a prompt followed by a JSON array of texts
    stdout : a JSON array of polarities (floats in [-1, 1]), same length

Wire it up in <vault>/soul/_config.yaml:
    emotion_backend: hybrid          # lexicon does the easy ones; LLM the rest
    emotion_llm_command: "python /path/to/emotion_llm_example.py"

Env:
    OPENTSC_EMOTION_API_URL   OpenAI-compatible chat/completions endpoint
    OPENTSC_EMOTION_API_KEY   bearer token
    OPENTSC_EMOTION_MODEL     model id (default: gpt-4o-mini-equivalent of your provider)

This is a reference implementation — swap in any provider. It reads the whole
batch from stdin and returns one JSON array, so the whole index build is a
handful of calls, not one per message.
"""

import json
import os
import sys
import urllib.request


def main() -> None:
    raw = sys.stdin.read()
    start = raw.find("[")
    texts = json.loads(raw[start:]) if start != -1 else []
    if not texts:
        print("[]")
        return

    url = os.environ.get("OPENTSC_EMOTION_API_URL", "")
    key = os.environ.get("OPENTSC_EMOTION_API_KEY", "")
    model = os.environ.get("OPENTSC_EMOTION_MODEL", "gpt-4o-mini")
    if not url:
        # No endpoint configured → neutral, so the pipeline degrades safely.
        print(json.dumps([0.0] * len(texts)))
        return

    instruction = (
        "为每段中文文本判断说话者情绪极性，返回一个等长 JSON 数组，"
        "每项是 -1.0(极负)到 1.0(极正) 的浮点数，只输出 JSON 数组。\n"
        + json.dumps(texts, ensure_ascii=False)
    )
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": instruction}],
        "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = json.loads(resp.read())["choices"][0]["message"]["content"]
        s = content[content.find("[") : content.rfind("]") + 1]
        scores = json.loads(s)
        if len(scores) != len(texts):
            scores = [0.0] * len(texts)
    except Exception:
        scores = [0.0] * len(texts)
    print(json.dumps([float(x) for x in scores]))


if __name__ == "__main__":
    main()
