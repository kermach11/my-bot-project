import os
from dotenv import load_dotenv

# Завантажуємо змінні з зовнішнього env-файлу
load_dotenv("C:/Users/DC/env_files/env")

# Доступ до ключа
API_KEY = os.getenv("OPENAI_API_KEY")

# Основні шляхи
base_path = r"C:\Users\DC\my-bot-project"
request_file = os.path.join(base_path, "cache.txt")
response_file = os.path.join(base_path, "gpt_response.json")
history_file = os.path.join(base_path, "ben_history.log")
memory_file = os.path.join(base_path, ".ben_memory.json")
