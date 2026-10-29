# 題 2｜結構化抽取＋逐欄位查核
- 主程式 [extractor.py](extractor.py)
- 資料格式 [schema.py](schema.py)
- 連接模型 [llm_client.py](llm_client.py)
- 假模型 [mock_llm.py](mock_llm.py)
- 測試程式碼 [tests/test_q2_extractor.py](../tests/test_q2_extractor.py)


## AI 協作
- 我請 Claude 規劃 schema、實作查核、錯誤處理、測試。
- 我調整程式碼。


## 1. 使用方法
- **安裝套件**：`poetry install`
- **執行程式碼**：`poetry run python -m q2_extraction.extractor "我在 10/12 訂的訂單 A20261012-5531，只收到一件，請盡快補寄。"`
- **跑測試**：`poetry run pytest tests/test_q2_extractor.py -v`
- **修改模型**：`cp .env.example .env`，調整`.env`的`LLM_MODEL`。
```
# 假模型的示範輸出，非真實 LLM 結果。
{
  "status": "ok",
  "data": {
    "categories": [
      "missing_item"
    ],
    "categories_evidence": "只收到",
    "order_id": "A20261012-5531",
    "order_id_evidence": "A20261012-5531",
    "request": "請客服協助處理",
    "request_evidence": "我在 10/12 訂",
    "urgency": "high",
    "urgency_evidence": "盡快"
  },
  "problems": [],
  "attempts": 1
}
```


## 2. 流程
```
客訴文字
   ↓
呼叫模型
   ↓
[呼叫失敗]
Gateway error ，等 1-2 秒再呼叫一次

[呼叫成功]
工具解析內容（不合法 JSON、缺欄位、沒用工具）
程式查核內容（解析出來的欄位值，是否在原文裡）
   ↓
[通過] 回傳 ok
[不通過] 把原因告訴模型請它重做，最多呼叫 3 次，失敗回傳 needs_review / gateway_error
```


## 3. Schema
請模型回傳的內容，包含問題類別、訂單編號、客人訴求、急迫程度、原文依據。
```json
{
  "categories": ["missing_item"],
  "categories_evidence": "只收到一件",
  "order_id": "A20261012-5531",
  "order_id_evidence": "訂單 A20261012-5531",
  "request": "補寄少收的外套",
  "request_evidence": "請盡快補寄",
  "urgency": "high",
  "urgency_evidence": "盡快"
}
```


## 4. 錯誤處理
- **`openai.APIError` Gateway 逾時、429呼叫太頻繁或配額不足，等 1-2 秒再重試。**
- **`parse()` 呼叫工具錯誤，告訴模型錯誤原因並重試。**
  - 模型沒呼叫工具：`message.tool_calls` 是空的。
  - 模型回傳不合法的JSON：`json.loads` 回傳 `JSONDecodeError`。
  - 缺欄位或型別錯誤：`pydantic` 回傳 `ValidationError`。
- **`check_grounding()` 查核錯誤，告訴模型錯誤原因並重試。**
  - `normalize()`：先把原文和 evidence 都全形轉半形、去掉空白。
  - `categories`、`request`、 `urgency=high` 的 evidence 必須是原文的片段。
  - `order_id` 必須符合格式且出現在原文片段。


## 5. 重試方式
- **整筆重試**：輸出欄位少，且欄位之間有關聯，分開重做可能互相矛盾。
- **重試次數**：最多呼叫 3 次（第一次+重試 2 次），重試時會把具體原因告訴模型，已經告訴原因還錯兩次，多半是模型不會或原文不清楚，再試只是增加費用與等待時間。
- **失敗輸出**：不輸出資料，顯示狀態為 `needs_review`、`data=None`，在 `problems` 寫原因並轉人工處理，因為沒有根據的值比空白危險。 


## 6. 產出結果
`ExtractionResult.status`
- `ok`：查核通過，可使用 data。
- `needs_review`：模型重試後仍不合格，轉人工處理，problems 可看原因。
- `gateway_error`：稍後再試。


