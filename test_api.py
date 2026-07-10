"""M0 验收脚本:验证 DeepSeek API 连通性。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    temperature=0,
    messages=[{"role": "user", "content": "请用一句话确认你收到了这条消息。"}],
)
print(resp.choices[0].message.content)
