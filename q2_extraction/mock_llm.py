"""假模型：
用法和 openai 的 client.chat.completions.create 一樣，測試與沒有金鑰時使用。

- MockLLM([回應, 例外, ...])：照順序回應，可模擬「捏造單號、壞 JSON、429、逾時」。
- MockLLM()：沒給劇本時，用幾個關鍵字自動產生合法結果（示範用，不是真的 NLP）。
"""
import copy
import json
import re
from types import SimpleNamespace

import httpx
import openai

from q2_extraction.schema import TOOL_NAME


class Message:
    """仿 SDK 的 message：有 content、tool_calls，以及 model_dump()。"""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, **_):
        data = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {
                    "name": c.function.name, "arguments": c.function.arguments}}
                for c in self.tool_calls
            ]
        return data


def text_response(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=Message(content=content))])


def tool_calls_response(calls):
    """calls: [(call_id, 函式名, 參數)]；參數給 str 就原樣送出（可用來造壞 JSON）。"""
    tool_calls = [
        SimpleNamespace(id=call_id, function=SimpleNamespace(
            name=name, arguments=args if isinstance(args, str) else json.dumps(args, ensure_ascii=False)))
        for call_id, name, args in calls
    ]
    return SimpleNamespace(choices=[SimpleNamespace(message=Message(tool_calls=tool_calls))])


def extraction_response(args):
    return tool_calls_response([("call_1", TOOL_NAME, args)])


# 仿 Gateway 的錯誤
def _request():
    return httpx.Request("POST", "https://llm-gateway.example.internal/v1/chat/completions")


def make_rate_limit_error():
    return openai.RateLimitError("rate limited", response=httpx.Response(429, request=_request()), body=None)


def make_timeout_error():
    return openai.APITimeoutError(request=_request())


class MockLLM:
    def __init__(self, script=None):
        self.script = None if script is None else list(script)  # None = 自動回答
        self.calls = []  # 每次呼叫的參數，測試用來檢查
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs))
        if self.script is None:
            # [0]=system, [1]=客訴原文
            return auto_response(kwargs["messages"][1]["content"])
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def auto_response(text):
    order = re.search(r"[A-Z]\d{5,}(?:-\d+)?", text)
    urgent = next((w for w in ["盡快", "很急", "立刻", "馬上"] if w in text), None)
    category, evidence = next(
        ((c, w) for c, w in [("missing_item", "只收到"),
         ("defective", "壞了"), ("membership", "點數")] if w in text),
        ("other", text.strip()[:10]),
    )
    return extraction_response({
        "categories": [category],
        "categories_evidence": evidence,
        "order_id": order.group(0) if order else None,
        "order_id_evidence": order.group(0) if order else None,
        "request": "請客服協助處理",
        "request_evidence": text.strip()[:10],
        "urgency": "high" if urgent else "normal",
        "urgency_evidence": urgent,
    })
