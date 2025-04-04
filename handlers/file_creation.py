import os
import time

def handle_create_file(cmd, base_path="."):
    filename = cmd.get("filename")
    content = cmd.get("content", "")
    if not filename:
        return {"status": "error", "message": "❌ Не вказано ім'я файлу"}

    full_file_path = os.path.join(base_path, filename)

    try:
        with open(full_file_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # 💾 Запис на диск

        time.sleep(0.1)  # ⏳ Даємо час

        return {"status": "success", "message": f"✅ Created file '{filename}'"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Не вдалося створити файл: {e}"}

def handle_create_and_finalize_script(cmd, base_path="."):
    try:
        script_name = cmd.get("file_path") or cmd.get("parameters", {}).get("file_path")
        script_content = cmd.get("content") or cmd.get("parameters", {}).get("content")

        if not script_name:
            return {"status": "error", "message": "❌ Не вказано імʼя скрипту (file_path)"}

        full_path = os.path.join(base_path, script_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(script_content or "")

        # Фіналізаційні дії (можна додати будь-що, наприклад: chmod, логування)

        return {"status": "success", "message": f"🎉 Скрипт створено та фіналізовано: {script_name}"}

    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка при створенні скрипту: {str(e)}"}
