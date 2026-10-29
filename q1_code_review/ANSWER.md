# 題 1｜程式碼審查：這隻 Agent 有什麼問題？
- 原始程式碼 [original_agent.py](original_agent.py)
- 修改程式碼 [fixed_agent.py](fixed_agent.py)
- 測試程式碼 [tests/test_q1_fixed_agent.py](../tests/test_q1_fixed_agent.py)


## AI 協作
- 我先提出看到的問題與修改方式。
  - API Key 明碼寫在程式碼。
  - SQL injection。
  - 缺少使用者權限驗證。
- 請 Claude 列出完整問題清單與嚴重性、理解問題。
- 先修改嚴重的問題。


## 1. 問題清單

| 編號 | 嚴重度 | 類別 | 問題 | 什麼情況會出事 |
|---|---|---|---|---|
| 1 | 嚴重 | 資安 | `get_order`和`cancel_order`拼接字串會 SQL injection| 使用者輸入 `x' OR '1'='1`，`cancel_order` 會取消所有訂單 |
| 2 | 嚴重 | 資安 | 缺少使用者權限驗證，工具只接收 `order_id`，沒有驗證 `current_user_id` | 任何人有訂單編號就可以查詢或取消別人的訂單|
| 3 | 嚴重 | 正確 | 取消沒有確認訂單狀態 | 已出貨的訂單被取消 |
| 4 | 嚴重 | 資安/穩定 | `globals()[call.function.name](**args)` 模型可以呼叫任何全域函式，還能塞任意參數 | 模型回傳非預期的函式名稱時，可能執行其他已存在的全域函式 |
| 5 | 嚴重 | 資安 | `api_key` 寫死在原始碼 | 金鑰外洩被盜用 |
| 6 | 高 | 正確 | 沒有把模型要求呼叫工具的 assistant 訊息放進 `messages`，就直接加工具回傳的結果 | API 規定 `tool` 訊息必須接在 `tool_calls` 訊息後面 |
| 7 | 高 | 成本 | `while True` 無窮迴圈 | 模型反覆呼叫工具或卡在錯誤中，燒光額度 |
| 8 | 高 | 穩定 | `json.loads` 取得模型回傳參數，沒有驗證就傳給函式 | 參數錯誤會讓請求失敗 |
| 9 | 中 | 成本/資安 | `SELECT *` 全部欄位都給模型 | 浪費 token；把個資送進模型違反最小揭露 |
| 10 | 中 | 成本 | 沒有 `max_tokens`，輸出長度不受限 | 成本與延遲暴增 |


## 2. 問題修改
- 問題 1+2+3：使用參數 `:order_id`、`:user_id`；SQL 條件加上由登入狀態傳進的 `current_user_id`，驗證使用者權限；SQL 條件加上可被取消的訂單狀態。
- 問題 4：設定模型可以呼叫的工具白名單，取代 `globals()`。
- 問題 5：金鑰、網址、模型名稱改讀環境變數。
- 問題 6：`messages` 加上模型要求呼叫工具的 assistant 訊息。
- 問題 7-10：未修改。
```
# messages 範例
[
    {
        "role": "system",
        "content": "你是訂單助理，幫客人查詢與取消訂單。"
    },
    {
        "role": "user",
        "content": "幫我查詢訂單 A123"
    },
    {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_order",
                    "arguments": "{\"order_id\": \"A123\"}"
                }
            }
        ]
    }
]
```



