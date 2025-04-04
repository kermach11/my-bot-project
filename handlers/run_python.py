import os
import subprocess
import json
import time

def handle_run_python(cmd):
    filename = cmd.get("filename") or cmd.get("parameters", {}).get("filename")
    if not filename:
        return {"status": "error", "message": "❌ Не вказано файл для виконання"}

    full_file_path = os.path.abspath(filename)
    if not os.path.exists(full_file_path):
        return {"status": "error", "message": f"❌ Файл '{filename}' не знайдено"}

    try:
        process = subprocess.run(
            ["python", "-u", full_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        time.sleep(0.1)

        parsed_result = ""
        last_result_path = os.path.join(os.path.dirname(full_file_path), "last_result.json")

        if os.path.exists(last_result_path):
            try:
                with open(last_result_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    parsed_result = data.get("parsed_result", "")
            except Exception as read_err:
                print(f"⚠️ Помилка при читанні last_result.json: {read_err}")

        return {
            "status": "success" if process.returncode == 0 else "error",
            "results": [{"parsed_result": parsed_result}] if parsed_result else [],
            "output": process.stdout,
            "errors": process.stderr
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Виняток при виконанні: {e}"
        }
