"""把 Q2 的抽取功能包成 HTTP 服務。
"""


import json
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from q2_extraction import llm_client
from q2_extraction.extractor import extract
from q2_extraction.schema import ExtractionResult

logging.basicConfig(level=logging.INFO)  # 讓 log 輸出到 stdout，容器平台才收得到
logger = logging.getLogger("complaint_api")
sleep = time.sleep  # 測試時換成不等待的函式

app = FastAPI(title="Complaint Extraction API")


class ExtractRequest(BaseModel):
    # 長度 1~5000：控制成本；pattern=\S：至少要有一個非空白字元
    text: str = Field(min_length=1, max_length=5000, pattern=r"\S")


class ExtractResponse(BaseModel):
    request_id: str
    result: ExtractionResult


@app.get("/healthz")
def healthz():
    """健康檢查：只確認服務活著，不呼叫模型。"""
    return {"status": "alive"}


@app.post("/v1/extract", response_model=ExtractResponse)
def extract_endpoint(body: ExtractRequest):
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    result = extract(body.text, llm_client.client,
                     llm_client.MODEL, sleep=sleep)

    # log 只記「發生了什麼」，不記客訴原文；訂單編號只留末 4 碼
    order_id = result.data.order_id if result.data else None
    logger.info(json.dumps({
        "request_id": request_id,
        "status": result.status,
        "attempts": result.attempts,
        "model": llm_client.MODEL,
        "text_len": len(body.text),
        "order_id": "****" + order_id[-4:] if order_id and len(order_id) > 4 else None,
        "latency_ms": round((time.monotonic() - started) * 1000),
    }, ensure_ascii=False))

    if result.status == "gateway_error":
        return JSONResponse(status_code=503, content={"detail": "模型服務暫時無法使用", "request_id": request_id})
    return ExtractResponse(request_id=request_id, result=result)
