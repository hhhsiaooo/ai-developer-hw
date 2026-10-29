import os
import sqlite3

import pytest

# fixed_agent 在 import 時就會建立 client，所以要先有環境變數
os.environ.setdefault("LLM_BASE_URL", "https://llm-gateway.example.internal/v1")
os.environ.setdefault("LLM_API_KEY", "test-key-not-real")

from q1_code_review import fixed_agent as agent  # noqa: E402
from q2_extraction.mock_llm import MockLLM, text_response, tool_calls_response  # noqa: E402


class FakeDB:
    """假的 db：包一層 sqlite3，介面對應原題的 db.query / db.execute。"""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE orders (id TEXT, user_id TEXT, status TEXT)")
        self.conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [("A1001", "u1", "pending"), ("A1002", "u1", "shipped"), ("B2001", "u2", "pending")],
        )

    def query(self, sql, params):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def execute(self, sql, params):
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor

    def status_of(self, order_id):
        return self.conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()["status"]


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(agent, "db", fake, raising=False)  # 原始程式沒有定義 db
    return fake


def run_with(monkeypatch, responses):
    mock = MockLLM(responses)
    monkeypatch.setattr(agent, "client", mock)
    return mock


# ───── 問題 1+2+3：SQL ─────
def test_get_order_only_returns_own_order(db):
    assert [r["id"] for r in agent.get_order("A1001", "u1")] == ["A1001"]
    assert agent.get_order("B2001", "u1") == []  # 別人的訂單


def test_sql_injection_string_is_just_an_id(db):
    assert agent.get_order("x' OR '1'='1", "u1") == []
    agent.cancel_order("x' OR '1'='1", "u1")
    assert db.status_of("A1001") == "pending" and db.status_of("B2001") == "pending"


def test_cancel_only_own_pending_order(db):
    agent.cancel_order("A1001", "u1")
    agent.cancel_order("A1002", "u1")  # 已出貨
    agent.cancel_order("B2001", "u1")  # 別人的
    assert db.status_of("A1001") == "cancelled"
    assert db.status_of("A1002") == "shipped"
    assert db.status_of("B2001") == "pending"


# ───── 問題 4：白名單 ─────
def test_unknown_tool_is_rejected(monkeypatch, db):
    mock = run_with(monkeypatch, [tool_calls_response([("c1", "run", {"order_id": "A1001"})]), text_response("ok")])
    agent.run("hi", "u1")
    assert mock.calls[1]["messages"][-1]["content"] == "不支援的工具"


def test_model_cannot_override_user_id(monkeypatch, db):
    args = {"order_id": "B2001", "current_user_id": "u2"}  # 模型想冒充 u2
    run_with(monkeypatch, [tool_calls_response([("c1", "cancel_order", args)]), text_response("ok")])
    agent.run("取消 B2001", "u1")
    assert db.status_of("B2001") == "pending"


# ───── 問題 6：assistant 訊息 ─────
def test_assistant_message_precedes_tool_message(monkeypatch, db):
    mock = run_with(monkeypatch, [tool_calls_response([("c1", "get_order", {"order_id": "A1001"})]), text_response("待處理")])
    assert agent.run("查 A1001", "u1") == "待處理"
    assert [m["role"] for m in mock.calls[1]["messages"]] == ["system", "user", "assistant", "tool"]
