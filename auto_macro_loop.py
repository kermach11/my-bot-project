import time
import json
from datetime import datetime
from gpt_interpreter import interpret_user_prompt

INTERVAL_MINUTES = 10

def log_debug(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("debug.log", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def loop():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] ⏳ GPT автооновлення макросу...")
            log_debug("⏳ GPT автооновлення макросу...")

            # 🔁 Оновлення макросу
            prompt = "Онови макрос, щоб покращити роботу з файлами"
            gpt_result = interpret_user_prompt(prompt)

            with open("macro_command.json", "w", encoding="utf-8") as f:
                json.dump(gpt_result, f, indent=2)

            print(f"[{now}] ✅ Макрос оновлено!")
            log_debug("✅ Макрос оновлено")

            # 🔍 Автоперевірка коду
            try:
                result = interpret_user_prompt("Проаналізуй якість коду в проекті та знайди слабкі місця")
                with open("autocheck_report.txt", "w", encoding="utf-8") as f:
                    f.write(result)
                print("🧪 Автоперевірка завершена")
                log_debug("🧪 Автоперевірка завершена")
            except Exception as e:
                err_msg = f"❌ Помилка під час автоперевірки: {e}"
                print(err_msg)
                log_debug(err_msg)

        except Exception as e:
            err_msg = f"❌ Помилка під час циклу: {e}"
            print(err_msg)
            log_debug(err_msg)

        time.sleep(INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    loop()
