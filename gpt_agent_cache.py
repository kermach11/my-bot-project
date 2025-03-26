import os
import json
from colorama import init, Fore, Style
init()
import time
import re
import shutil
import subprocess
from datetime import datetime, timezone

base_path = r"C:\\Users\\DC\\my-bot-project"
request_file = os.path.join(base_path, "cache.txt")
response_file = os.path.join(base_path, "gpt_response.json")
history_file = os.path.join(base_path, "ben_history.log")

def log_action(message):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def read_requests():
    if not os.path.exists(request_file):
        return []
    with open(request_file, "r", encoding="utf-8") as f:
        try:
            text = f.read().strip()
            if not text:
                return []
            data = json.loads(text)
            return data if isinstance(data, list) else [data]
        except Exception as e:
            return [{"status": "error", "message": f"❌ JSON error: {str(e)}"}]

def write_response(responses):
    with open(response_file, "w", encoding="utf-8") as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)

def clear_cache():
    with open(request_file, "w", encoding="utf-8") as f:
        f.write("")

def handle_command(cmd):
    try:
        action = cmd.get("action")
        filename = cmd.get("filename")
        foldername = cmd.get("foldername")
        content = cmd.get("content", "")
        pattern = cmd.get("pattern")
        replacement = cmd.get("replacement")
        target_folder = cmd.get("target_folder")
        new_name = cmd.get("new_name")

        full_file_path = os.path.join(base_path, filename) if filename else None
        full_folder_path = os.path.join(base_path, foldername) if foldername else None
        dst_folder_path = os.path.join(base_path, target_folder) if target_folder else None
        dst_file_path = os.path.join(dst_folder_path, filename) if target_folder and filename else None

        if action == "create_file":
            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"✅ Created file '{filename}'"}

        elif action == "append_file":
            with open(full_file_path, "a", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"📌 Appended to file '{filename}'"}
        elif action == "scan_all_files":
            result = {}
            for fname in os.listdir(base_path):
                fpath = os.path.join(base_path, fname)
                if os.path.isfile(fpath) and fname.endswith((".py", ".json", ".txt", ".csv")):
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            result[fname] = f.read()
                    except Exception as e:
                        result[fname] = f"⚠️ Error reading: {str(e)}"
            return {"status": "success", "files": result}

        elif action == "update_file":
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    data = f.read()
                updated = re.sub(pattern, replacement, data)
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                return {"status": "success", "message": f"🔁 Updated file '{filename}'"}
            else:
                return {"status": "error", "message": "File not found"}

        elif action == "replace_in_file":
    if filename in ["config.py", "api_keys.py", "cache.txt", "gpt_agent_cache.py"]:
        return {"status": "error", "message": f"❌ Заборонено змінювати критичний файл: {filename}"}
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                import re
                new_text = re.sub(pattern, replacement, text)
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
                return {"status": "success", "message": f"✏️ Replaced text in '{filename}'"}

        elif action == "read_file":
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    return {"status": "success", "content": f.read()}
            return {"status": "error", "message": "File not found"}

        elif action == "search_text_in_file":
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                matches = [line for line in lines if pattern in line]
                return {"status": "success", "matches": matches}

        elif action == "create_folder":
            os.makedirs(full_folder_path, exist_ok=True)
            return {"status": "success", "message": f"📁 Folder '{foldername}' created"}

        elif action == "delete_file":
            if os.path.exists(full_file_path):
                os.remove(full_file_path)
                return {"status": "success", "message": f"🗑️ File '{filename}' deleted"}
            else:
                return {"status": "error", "message": f"File '{filename}' not found"}

        elif action == "rename_file":
            new_path = os.path.join(base_path, new_name)
            os.rename(full_file_path, new_path)
            return {"status": "success", "message": f"📄 File renamed to '{new_name}'"}

        elif action == "copy_file":
            shutil.copy(full_file_path, dst_file_path)
            return {"status": "success", "message": f"📂 Copied '{filename}' to '{target_folder}'"}

        elif action == "read_folder":
            if os.path.exists(full_folder_path):
                files = os.listdir(full_folder_path)
                return {"status": "success", "files": files}
            return {"status": "error", "message": "Folder not found"}

        elif action == "run_python":
            result = subprocess.run(["python", full_file_path], capture_output=True, text=True)
            return {"status": "success", "output": result.stdout, "errors": result.stderr}

        elif action == "macro":
            results = []
            for step in cmd.get("steps", []):
                result = handle_command(step)
                results.append(result)
            return {"status": "success", "steps": results}

        elif action == "list_files":
            return {"status": "success", "files": os.listdir(base_path)}

        elif action == "check_status":
            return {"status": "success", "message": "🟢 Agent is running"}

        else:
            return {"status": "error", "message": f"❌ Unknown action: {action}"}

    except Exception as e:
        return {"status": "error", "message": f"❌ Exception: {str(e)}"}

if __name__ == "__main__":
    print("🟢 Бен запущений і слухає команди з cache.txt...")
    while True:
        commands = read_requests()
        print("📩 Отримано команди:", commands)  # Показує, чи щось є в cache.txt

        responses = []
        for cmd in commands:
            result = handle_command(cmd)
            print("✅ Виконано:", result)  # Показує результат кожної дії
            responses.append(result)
            log_action(result.get("message", str(result)))

        if responses:
            print("💾 Записую gpt_response.json і очищаю cache.txt")
            write_response(responses)
            clear_cache()

        time.sleep(1)
