import logging

import pytest
from fastapi.testclient import TestClient

from q2_extraction import llm_client
from q2_extraction.mock_llm import MockLLM, extraction_response, make_rate_limit_error
from q4_service import app as app_module
from tests.samples import S1, VALID


@pytest.fixture
def make_client(monkeypatch):
    """用假模型照劇本回應，並讓重試不用真的等待。"""
    def make(script):
        llm = MockLLM(script)
        monkeypatch.setattr(llm_client, "client", llm)
        monkeypatch.setattr(app_module, "sleep", lambda s: None)
        return TestClient(app_module.app), llm
    return make


def test_healthz_ok(make_client):
    client, _ = make_client([])
    assert client.get("/healthz").status_code == 200


def test_extract_ok(make_client):
    text, args = VALID["s1"]
    client, _ = make_client([extraction_response(args)])
    resp = client.post("/v1/extract", json={"text": text})
    assert resp.status_code == 200
    assert resp.json()["result"]["status"] == "ok"


def test_extract_needs_review_still_200(make_client):
    text, args = VALID["s1"]
    fake = {**args, "order_id": "A20261012-9999"}  # 模型一直捏造單號
    client, _ = make_client([extraction_response(fake)] * 3)
    resp = client.post("/v1/extract", json={"text": text})
    assert resp.status_code == 200
    assert resp.json()["result"]["status"] == "needs_review"


@pytest.mark.parametrize("text", ["", "   ", "字" * 5001])
def test_invalid_text_returns_422_without_calling_model(make_client, text):
    client, llm = make_client([])
    assert client.post("/v1/extract", json={"text": text}).status_code == 422
    assert llm.calls == []


def test_gateway_429_returns_503(make_client):
    client, _ = make_client([make_rate_limit_error()] * 3)
    assert client.post("/v1/extract", json={"text": S1}).status_code == 503


def test_logs_do_not_contain_raw_text_or_full_order_id(make_client, caplog):
    caplog.set_level(logging.INFO, logger="complaint_api")
    text, args = VALID["s1"]
    client, _ = make_client([extraction_response(args)])
    request_id = client.post("/v1/extract", json={"text": text}).json()["request_id"]
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "只收到一件" not in logs and "A20261012-5531" not in logs
    assert "****5531" in logs and request_id in logs
