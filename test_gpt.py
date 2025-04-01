# test_gpt.py

from openai import OpenAI
from dotenv import load_dotenv
import os

# Завантаження змінних із .env
load_dotenv("C:/Users/DC/env_files/env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

res = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Say hello"}]
)

print(res.choices[0].message.content)
