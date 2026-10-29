import pytest

from q2_extraction.extractor import check_grounding, extract
from q2_extraction.mock_llm import (
    MockLLM,
    extraction_response,
    make_rate_limit_error,
    make_timeout_error,
    text_response,
)
from q2_extraction.schema import Extraction
from tests.samples import S1, VALID


@pytest.fixture
def slept():
    return []


def run(text, script, slept):
    client = MockLLM(script)
    result = extract(text, client, "chat-default", sleep=slept.append)
    return result, client


# ───── 正常案例 ─────
@pytest.mark.parametrize("key", ["s1", "s2", "s3"])
def test_normal_sample_returns_ok(key, slept):
    text, args = VALID[key]
    result, _ = run(text, [extraction_response(args)], slept)
    assert result.status == "ok"
    assert result.attempts == 1
    assert result.data.order_id == args["order_id"]


# ───── 模型捏造訂單編號 ─────
def test_fabricated_order_id_retries_then_recovers(slept):
    text, args = VALID["s1"]
    fake = {**args, "order_id": "A20261012-9999"}
    result, client = run(text, [extraction_response(fake), extraction_response(args)], slept)
    assert result.status == "ok"
    assert result.attempts == 2
    feedback = client.calls[1]["messages"][-1]["content"]  # 錯誤原因有告訴模型
    assert "order_id" in feedback and "未出現在原文" in feedback


def test_fabricated_order_id_exhausted_needs_review(slept):
    text, args = VALID["s1"]
    fake = {**args, "order_id": "A20261012-9999"}
    result, _ = run(text, [extraction_response(fake)] * 3, slept)
    assert result.status == "needs_review"
    assert result.data is None  # 不輸出未經驗證的資料
    assert result.attempts == 3
    assert any("order_id" in p for p in result.problems)


# ───── JSON 格式錯誤、缺欄位 ─────
def test_invalid_json_retries_then_recovers(slept):
    text, args = VALID["s1"]
    result, _ = run(text, [extraction_response("{not json"), extraction_response(args)], slept)
    assert result.status == "ok"
    assert result.attempts == 2


def test_invalid_json_exhausted_needs_review(slept):
    text, _ = VALID["s1"]
    result, _ = run(text, [extraction_response("{not json")] * 3, slept)
    assert result.status == "needs_review"
    assert result.problems == ["工具參數不是合法 JSON"]


def test_missing_field_is_reported_to_model(slept):
    text, args = VALID["s1"]
    incomplete = {k: v for k, v in args.items() if k != "urgency"}
    result, client = run(text, [extraction_response(incomplete), extraction_response(args)], slept)
    assert result.status == "ok"
    assert "urgency" in client.calls[1]["messages"][-1]["content"]


# ───── Gateway 逾時、429 ─────
def test_timeout_then_success(slept):
    text, args = VALID["s1"]
    result, _ = run(text, [make_timeout_error(), extraction_response(args)], slept)
    assert result.status == "ok"
    assert slept == [1]


def test_rate_limit_always_returns_gateway_error(slept):
    text, _ = VALID["s1"]
    result, _ = run(text, [make_rate_limit_error()] * 3, slept)
    assert result.status == "gateway_error"
    assert slept == [1, 2]  # 最後一次失敗後不再等


# ───── 查核規則 ─────
def check(text, **overrides):
    _, args = VALID["s1"]
    return check_grounding(Extraction.model_validate({**args, **overrides}), text)


def test_grounded_extraction_passes():
    assert check(S1) == []


def test_evidence_not_in_source_is_flagged():
    assert check(S1, categories_evidence="完全沒出現") == ["categories: evidence 未出現在原文"]


def test_null_order_id_is_ok_without_evidence():
    assert check(S1, order_id=None, order_id_evidence=None) == []


def test_fullwidth_order_id_in_source_is_grounded():
    source = "我的訂單Ａ２０２６１０１２－５５３１只收到一件，請盡快補寄，很盡快"
    assert check(source, order_id_evidence="訂單Ａ２０２６１０１２－５５３１") == []


# ───── 設定：換模型 ─────
def test_model_name_is_passed_to_client(slept):
    text, args = VALID["s1"]
    client = MockLLM([extraction_response(args)])
    extract(text, client, "chat-cheap", sleep=slept.append)
    assert client.calls[0]["model"] == "chat-cheap"
