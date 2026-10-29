# 題 4｜把它變成一個服務
- API 程式 [app.py](app.py)
- Dockerfile [Dockerfile](../Dockerfile)
- 測試程式碼 [tests/test_q4_api.py](../tests/test_q4_api.py)


## AI 協作
- 我先提出自己的想法：用 FastAPI 和 Docker、log 不存放個資。
- 請 Claude 給予建議並實作。


## 1. 使用方法 (未實際建置並執行容器)
- 建置並執行容器：先 `cp .env.example .env`，`docker build -t complaint-api .`、`docker run --rm -p 8000:8000 --env-file .env complaint-api`
- 啟動服務：`poetry run uvicorn q4_service.app:app --reload`
- 試打 API：`http://127.0.0.1:8000/docs`
- 跑測試：`poetry run pytest tests/test_q4_api.py -v`


## 2. API
- `POST /v1/extract`：回傳 {request_id, result}。
- `GET /healthz`：健康檢查只確認服務活著。

| 狀況 | HTTP |
|---|---|
| 成功 | 200，`result.status` 為 `ok`(data可用) 或 `needs_review`(轉人工處理) |
| 格式空白或過長 | 422，不呼叫模型 |
| Gateway 錯誤 | 503，請稍後再試 |

## 3. Dockerfile
- 基底映像 `python:3.12-slim`。
- 複製 `pyproject.toml`、`poetry.lock` 安裝套件。
- 複製 `q2_extraction`、`q4_service` 服務程式碼。
- 用非 root 的使用者執行。
- `HEALTHCHECK` 呼叫 `/healthz`，不呼叫模型。
- `.dockerignore` 排除 `.env` 。


## 4. 金鑰設定
- 金鑰不放進映像檔，容器啟動時才用環境變數傳進去，更換金鑰或設定後須重啟容器。
- 本機用 --env-file，上線後用平台 Secret 設成環境變數。


## 5. 健康檢查
- `/healthz`（存活檢查）只確認服務活著，不呼叫模型消耗額度。
- 設定不完整（缺金鑰或網址）時，程式啟動就會失敗，容器起不來，不另外做「就緒檢查」。


## 6. Log 紀錄
- 原則：記錄發生了什麼，不記個資姓名、電話、地址。
- 格式：單行 JSON，輸出到 stdout。

| 紀錄 | 不記錄 | 用途 |
|---|---|---|
| `request_id`、`status`、`attempts`、`latency_ms` | API key、Authorization header | 可以串連請求以排查問題、不外洩金鑰 |
| 原文長度 `text_len` | 客訴原文 | 可以判斷慢是不是因為信太長、不記錄個資 |
| 訂單編號末 4 碼（`****5531`） | 完整訂單編號 | 可以串查，不暴露完整單號 |


## 7. 排查順序

| 步驟 | 排查方式 | 意義 |
|---|---|---|
| 1 | 問題從什麼時候開始、多少比例、錯誤碼是什麼；最近有沒有部署或改設定 | 開始時間和部署或改設定吻合，先 rollback |
| 2 | 容器有沒有一直重啟、記憶體和 CPU 是否快滿 | 代表資源不足 |
| 3 | 用 `request_id` 找一筆慢的請求，看 log 裡的 `attempts` | `attempts` 大於 1 表示模型答得不好重試了|
| 4 | 檢查外部模型服務 429、5xx 的次數，以及本月剩餘額度 | 429 超頻請求；5xx 對方服務有問題 |