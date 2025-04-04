# handlers/macro_builder.py
import json
from config import API_KEY
from openai import OpenAI

def handle_macro_build(cmd):
    prompt = cmd.get("prompt") or cmd.get("parameters", {}).get("prompt")
    if not prompt:
        return {"status": "error", "message": "❌ Не вказано prompt для генерації макросу"}

    try:
        client = OpenAI(api_key=API_KEY)

        system_prompt = """
Ти асистент для генерації макрокоманд для кодувального агента.
На основі запиту користувача створи JSON-масив macro-кроків у форматі:

[
  {"action": "create_file", "filename": "example.py", "content": "..."},
  {"action": "update_code", "file_path": "example.py", "update_type": "logging"},
  {"action": "run_python", "filename": "example.py"}
]

Поверни ТІЛЬКИ масив JSON без пояснень.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        steps = json.loads(response.choices[0].message.content.strip())

        # 💾 Зберігаємо у файл для наочності
        with open("macro_output.json", "w", encoding="utf-8") as f:
            json.dump(steps, f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "message": "✅ Macro-кроки згенеровано",
            "steps": steps
        }

    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка генерації макрокоманди: {str(e)}"}
