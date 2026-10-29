# Q4：complaint extraction API
# build：docker build -t complaint-api .
# run  ：docker run --rm -p 8000:8000 --env-file .env complaint-api
#        （金鑰與設定在「執行時」才傳入，不會被打包進映像）
FROM python:3.12-slim
WORKDIR /app

# 先只裝套件：程式碼改動時，這一層可以重用快取
RUN pip install poetry
COPY pyproject.toml poetry.lock README.md ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

COPY q2_extraction ./q2_extraction
COPY q4_service ./q4_service

# 不用 root 執行
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# 只檢查服務是否活著，不呼叫模型
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
CMD ["uvicorn", "q4_service.app:app", "--host", "0.0.0.0", "--port", "8000"]
