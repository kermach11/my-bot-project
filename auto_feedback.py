import json
import os
from datetime import datetime
from gpt_interpreter import interpret_user_prompt

def run_feedback_analysis():
    print("🔄 Починаю аналіз...")

    try:
        with open("gpt_response.json", "r", encoding="utf-8") as f:
            response = json.load(f)

        filename = response.get("filename") or response.get("file_path")

        # 🛡️ Перевірка типу файлу — аналізувати тільки .py
        if filename and not filename.endswith(".py"):
            print(f"⚠️ Пропущено аналіз: '{filename}' не є Python-файлом")
            return

        prompt = f"""
Проаналізуй наступну відповідь GPT на виконану дію. Визнач:
- Чи результат відповідає очікуванню?
- Якщо ні — що виправити?
- Який наступний крок логічний?

Ось відповідь:
{json.dumps(response, indent=2, ensure_ascii=False)}
"""

        result = interpret_user_prompt(prompt)
        print(f"[DEBUG] GPT повернув:\n{result}\n")

        if not isinstance(result, str):
            raise ValueError("GPT повернув None або нестроковий результат")

        timestamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        filename = f"feedback_report_{timestamp}.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"📝 Feedback збережено: {filename}")

    except Exception as e:
        print(f"❌ Feedback помилка: {e}")

if __name__ == "__main__":
    print("✅ Імпорт пройшов успішно")
    run_feedback_analysis()
