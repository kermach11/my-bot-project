import json
import os

base_path = r"C:\Users\DC\my-bot-project"
cache_file = os.path.join(base_path, "cache.txt")

commands = [
    {
        "action": "create_folder",
        "foldername": "BEN_TEST_FOLDER"
    },
    {
        "action": "create_file",
        "filename": "ben_test.txt",
        "content": "🧠 Це тест з оновленим GPT-агентом!"
    }
]

with open(cache_file, "w", encoding="utf-8") as f:
    json.dump(commands, f, indent=2, ensure_ascii=False)

print("✅ Команди надіслані агенту через cache.txt!")
