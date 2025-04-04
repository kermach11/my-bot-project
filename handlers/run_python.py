import os
import time
import tempfile

time.sleep(0.2)

def handle_run_python(cmd):
    filename = cmd.get("filename")
    if not filename:
        return {"status": "error", "message": "❌ Не вказано файл для виконання"}

    full_file_path = os.path.abspath(filename)

    if not os.path.exists(full_file_path):
        return {"status": "error", "message": f"❌ Файл '{filename}' не знайдено"}

    print("⏳ Очікування завершення запису файлу...")
    time.sleep(0.2)

    try:
        result = subprocess.run(
            ["python", full_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            cwd=os.path.dirname(full_file_path),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"}
        )

        print("🧪 STDOUT repr:", repr(process.stdout))
        print("🧪 STDERR (обʼєднано в stdout): None")

        output = result.stdout.strip()

        print("📤 Output (repr):", repr(output))

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": output,
            "errors": ""
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Виняток при виконанні: {e}"
        }