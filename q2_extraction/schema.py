"""schema
"""


from typing import Literal
from pydantic import BaseModel, Field

TOOL_NAME = "submit_complaint_extraction"

Category = Literal["missing_item", "defective",
                   "shipping_delay", "membership", "refund_return", "other"]
Urgency = Literal["normal", "high"]


class Extraction(BaseModel):
    """模型要回傳的內容，需要查核，每個欄位都檢附原文片段 evidence。"""

    categories: list[Category] = Field(min_length=1)  # 問題類別，複合問題可有多個
    categories_evidence: str  # 原文依據
    order_id: str | None  # 信裡沒有就是 null，不准猜
    order_id_evidence: str | None  # 原文依據
    request: str  # 一句話表達客人訴求
    request_evidence: str  # 原文依據
    urgency: Urgency  # 有明確催促（如「盡快」）才給 high，沒有就 normal
    urgency_evidence: str | None  # 原文依據


class ExtractionResult(BaseModel):
    """交給呼叫端的結果。

    ok：查核通過，data 有值。
    needs_review：重試後仍不合格，data 為空，交給人工處理。
    gateway_error：Gateway 逾時、429 等重試後仍失敗。
    """

    status: Literal["ok", "needs_review", "gateway_error"]
    data: Extraction | None = None
    problems: list[str] = Field(default_factory=list)  # 最後一次失敗的原因
    attempts: int = 0


EXTRACTION_TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "提交從客訴信抽取出的結構化資料。每個 evidence 必須是原文的逐字片段。",
        "parameters": Extraction.model_json_schema(),
    },
}
