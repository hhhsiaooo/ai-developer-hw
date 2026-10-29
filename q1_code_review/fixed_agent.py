"""題 1 修正程式碼。

問題 1+2+3：使用參數 `:order_id`、`:user_id`；SQL 條件加上由登入狀態傳進的 `current_user_id`，驗證使用者權限；SQL 條件加上可取消的訂單狀態。
問題 4：設定模型可以呼叫的工具白名單，取代 globals()。
問題 5：金鑰、網址、模型名稱改讀環境變數。
問題 6：`messages` 加上模型要求呼叫工具的 assistant 訊息。
"""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 問題 5：金鑰、網址、模型名稱改讀環境變數。
client = OpenAI(base_url=os.environ["LLM_BASE_URL"],
                api_key=os.environ["LLM_API_KEY"])
MODEL = os.environ.get("LLM_MODEL", "chat-default")

TOOLS = [
    {"type": "function", "function": {
        "name": "get_order",
        "description": "查詢訂單",
        "parameters": {"type": "object",
                       "properties": {"order_id": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "cancel_order",
        "description": "取消訂單",
        "parameters": {"type": "object",
                       "properties": {"order_id": {"type": "string"}}}}},
]


# 問題 1+2+3：使用參數 `:order_id`、`:user_id`；SQL 條件加上由登入狀態傳進的 `current_user_id`，驗證使用者權限；SQL 條件加上可取消的訂單狀態。
def get_order(order_id, current_user_id):
    return db.query("SELECT * FROM orders WHERE id = :order_id AND user_id = :user_id",
                    {"order_id": order_id, "user_id": current_user_id})


def cancel_order(order_id, current_user_id):
    return db.execute("UPDATE orders SET status='cancelled' "
                      "WHERE id = :order_id AND user_id = :user_id AND status = 'pending'",
                      {"order_id": order_id, "user_id": current_user_id})


# 問題 4：設定模型可以呼叫的工具白名單，取代 globals()。
TOOL_HANDLERS = {"get_order": get_order, "cancel_order": cancel_order}


def run(user_message, current_user_id):
    messages = [{"role": "system", "content": "你是訂單助理，幫客人查詢與取消訂單。"},
                {"role": "user", "content": user_message}]
    while True:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content
        # 問題 6：`messages` 加上模型要求呼叫工具的 assistant 訊息。
        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            handler = TOOL_HANDLERS.get(call.function.name)
            if handler is None:
                result = "不支援的工具"
            else:
                result = handler(args["order_id"], current_user_id)
                # 加上由登入狀態傳進的 `current_user_id`，驗證使用者權限。
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": str(result)})
