"""連接模型：
1. 讀取環境變數（LLM_MODE、LLM_BASE_URL、LLM_API_KEY、LLM_MODEL）。
2. 預設用假模型。
3. LLM_MODE=real 時連 OpenAI 相容的 Gateway
"""


import os
from dotenv import load_dotenv
from openai import OpenAI
from q2_extraction.mock_llm import MockLLM

load_dotenv()

MODEL = os.environ.get("LLM_MODEL", "chat-default")  # 可換成 chat-cheap 模型

if os.environ.get("LLM_MODE", "mock") == "real":
    client = OpenAI(base_url=os.environ["LLM_BASE_URL"],
                    api_key=os.environ["LLM_API_KEY"],
                    timeout=30, max_retries=0)
else:
    client = MockLLM()
