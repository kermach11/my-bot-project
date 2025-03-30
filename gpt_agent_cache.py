def handle_command(cmd):
    if cmd.get("filename") == "env" or cmd.get("file_path", "").endswith("env"):
        if cmd["action"] in ["update_file", "append_file", "replace_in_file", "update_code", "delete_file"]:
            return {"status": "error", "message": "❌ Заборонено змінювати або комітити файл 'env'"}

import os
import json
from colorama import init, Fore, Style
init()
import time
import re
import ast
import shutil
import subprocess
import traceback
from datetime import datetime, timezone
from config import base_path, request_file, response_file, history_file
from config import API_KEY
from dotenv import load_dotenv
load_dotenv()
import os
API_KEY = os.getenv("OPENAI_API_KEY")
from gpt_interpreter import interpret_user_prompt
interpret_user_prompt("створи функцію, яка перевіряє, чи пароль має щонайменше 8 символів")



import sqlite3

import subprocess
def write_debug_log(message):
    debug_log_path = os.path.join(base_path, "debug.log")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def handle_run_shell(command):
    shell_cmd = command.get("command")
    if not shell_cmd:
        return {"status": "error", "message": "❌ Missing shell command"}

    try:
        print(f"[BEN] 💻 Running shell: {shell_cmd}")
        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "message": f"❌ Shell error: {result.stderr.strip()}"}
        return {"status": "success", "message": f"✅ Shell OK: {result.stdout.strip()}"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Shell exception: {e}"}

def create_history_table():
    conn = sqlite3.connect(os.path.join(base_path, "history.sqlite"))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            file_path TEXT,
            update_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
write_debug_log('🟢 Agent started and listening...')

def is_valid_python_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {filepath}: {e}")
        return False

create_history_table()

def log_action(message):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(history_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def save_to_memory(cmd):
    memory_file = os.path.join(base_path, ".ben_memory.json")
    try:
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                memory = json.load(f)
        else:
            memory = []
        cmd["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        memory.append(cmd)
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory[-100:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_action(f"⚠️ Error saving to memory: {str(e)}")

def handle_list_history():
    memory_file = os.path.join(base_path, ".ben_memory.json")
    if os.path.exists(memory_file):
        with open(memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
        return {"status": "success", "history": memory[-20:]}
    return {"status": "error", "message": "❌ Memory file not found"}

def get_history():
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(base_path, "history.sqlite"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM command_history ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
        conn.close()
        return {"status": "success", "history": rows}
    except Exception as e:
        return {"status": "error", "message": f"❌ Failed to fetch from SQLite: {e}"}

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

import difflib

def smart_deduplicate_insertion(existing_block, new_block):
    existing_lines = [line.strip() for line in existing_block.strip().splitlines()]
    new_lines = [line.strip() for line in new_block.strip().splitlines()]
    merged = existing_block.strip().splitlines()
    for line in new_lines:
        if line and line.strip() not in existing_lines:
            merged.append(line)
    return "\n".join(merged) + "\n"

def handle_update_code(command):
    file_path = command.get('file_path')
    update_type = command.get('update_type')  # 'validation', 'exceptions', 'logging', 'custom_insert', ...
    insert_at_line = command.get('insert_at_line')
    insert_code = command.get('code') 

    # 🆕 Підтримка простого формату без updates[]
    if "updates" not in command and all(k in command for k in ("pattern", "replacement", "update_type")):
        command["updates"] = [{
            "pattern": command["pattern"],
            "replacement": command["replacement"],
            "update_type": command["update_type"]
        }]

    if not file_path:
        return {"status": "error", "message": "❌ Missing 'file_path'"}

    # 🔁 Спеціальні типи
    if update_type in ("validation", "exceptions", "logging", "custom_insert"):
        test_result = handle_command({"action": "test_python", "filename": file_path})
        if test_result.get("status") == "error":
            return {"status": "error", "message": f"❌ Syntax check failed: {test_result.get('message')}"}

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if update_type == 'validation':
            lines.append('\nif data is None:\n    raise ValueError("Input data cannot be None")')
        elif update_type == 'exceptions':
            lines.append('\ntry:\n    risky_operation()\nexcept Exception as e:\n    print(f"Exception occurred: {e}")')
        elif update_type == 'logging':
            lines.append('\nimport logging\nlogging.basicConfig(level=logging.INFO)\nlogging.info("Log message from BEN")')
        elif update_type == 'custom_insert' and insert_code:
            if isinstance(insert_at_line, int) and 0 <= insert_at_line <= len(lines):
                lines.insert(insert_at_line, insert_code + '\n')
            else:
                return {"status": "error", "message": "❌ Invalid insert_at_line value"}

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        if not is_valid_python_file(file_path):
            return {"status": "error", "message": f"❌ Syntax error after applying update_code to {file_path}"}

        print(f"[BEN] update_code applied to {file_path} with type {update_type}")
        return {"status": "success", "message": f"✅ update_code applied to {file_path} with type {update_type}"}

    # 🔁 Універсальний режим: updates[]. Виконується тільки якщо НЕ один із вище
    updates = command.get("updates")
    if not updates:
        return {"status": "error", "message": "❌ Missing 'updates' or unsupported update_type"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return {"status": "error", "message": "❌ File not found"}

    # Зберегти .bak перед змінами
    backup_path = file_path + ".bak"
    with open(backup_path, "w", encoding="utf-8") as backup:
        backup.write(content)

    for upd in updates:
        pattern = upd.get("pattern")
        replacement = upd.get("replacement")
        u_type = upd.get("update_type")

        if not all([pattern, replacement, u_type]):
            return {"status": "error", "message": "❌ Missing fields in update"}

        import re
        if u_type == "replace":
            matches = list(re.finditer(pattern, content, flags=re.DOTALL))
            if not matches:
                return {"status": "error", "message": "❌ Pattern not found"}
            for match in reversed(matches):
                span = match.span()
                target = content[span[0]:span[1]]
                updated = smart_deduplicate_insertion(target, replacement)
                content = content[:span[0]] + updated + content[span[1]:]

        elif u_type == "append":
            content = smart_deduplicate_insertion(content, replacement)

        elif u_type == "prepend":
            content = smart_deduplicate_insertion(replacement, content)

        else:
            return {"status": "error", "message": f"❌ Unknown update_type: {u_type}"}


    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"status": "success", "message": f"✅ Updated {file_path}"}


def log_diff(filepath):
    try:
        result = subprocess.run(["git", "diff", filepath], capture_output=True, text=True)
        diff = result.stdout.strip()
        if diff:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(f"[DIFF {timestamp}] File: {filepath}\n{diff}\n---\n")
    except Exception as e:
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(f"[DIFF ERROR] {filepath}: {str(e)}\n")


def handle_macro(cmd):
    if not isinstance(cmd.get("steps"), list):
        return {"status": "error", "message": "❌ Invalid macro steps"}

    steps = cmd["steps"]
    rollback = cmd.get("rollback_on_fail", False)
    results = []
    created_files = []

    if rollback:
        for step in steps:
            if "filename" in step:
                file_path = os.path.join(base_path, step["filename"])
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        original = f.read()
                    with open(file_path + ".bak", "w", encoding="utf-8") as f:
                        f.write(original)

    for step in steps:
        result = handle_command(step)
        results.append(result)

        # Збираємо створені файли (для видалення у rollback)
        if step.get("action") == "create_file" and "filename" in step:
            created_files.append(step["filename"])

        if result.get("status") == "error" and rollback:
            # Відкат з резервних копій
            for s in steps:
                if "filename" in s:
                    file_path = os.path.join(base_path, s["filename"])
                    bak_file = file_path + ".bak"
                    if os.path.exists(bak_file):
                        with open(bak_file, "r", encoding="utf-8") as f:
                            restored = f.read()
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(restored)

            # Видаляємо новостворені файли
            for fname in created_files:
                file_path = os.path.join(base_path, fname)
                if os.path.exists(file_path):
                    os.remove(file_path)

            # 🧠 Запис rollback'у в памʼять
            save_to_memory({
                "action": "rollback",
                "reason": result.get("message"),
                "rollback_steps": steps
            })

            # ♻️ Git-коміт
            auto_commit("♻️ Rollback after failure")

            return {
                "status": "error",
                "message": "❌ Macro failed. Rolled back all changes.",
                "results": results
            }

    return {"status": "success", "steps": results}

def handle_command(cmd):
    if not isinstance(cmd, dict):
        return {"status": "error", "message": "❌ Invalid command format — expected a JSON object"}

    # 🛡️ Захист: перевірка на дублювання при вставці функцій
    if cmd.get("action") == "append_file" and "def " in cmd.get("content", ""):
        new_func_name = None
        try:
            new_func_ast = ast.parse(cmd["content"])
            for node in ast.walk(new_func_ast):
                if isinstance(node, ast.FunctionDef):
                    new_func_name = node.name  # <-- правильний відступ тут!
                    break  # <-- правильний відступ тут!
        except SyntaxError:
            return {"status": "error", "message": "❌ Syntax error in new function code"}

        if new_func_name:
            existing_file_path = os.path.join(base_path, cmd["filename"])
            if os.path.exists(existing_file_path):
                with open(existing_file_path, "r", encoding="utf-8") as f:
                    existing_ast = ast.parse(f.read())
                    for node in ast.walk(existing_ast):
                        if isinstance(node, ast.FunctionDef) and node.name == new_func_name:
                            return {
                                "status": "skipped",
                                "message": f"⚠️ Function '{new_func_name}' already exists in {cmd['filename']}"
                            }

    required_keys = ["action"]
    for key in required_keys:
        if key not in cmd:
            return {"status": "error", "message": f"❌ Missing required field: {key}"}
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
            save_to_memory(cmd)  
            return {"status": "success", "message": f"✅ Created file '{filename}'"}

        elif action == "update_code":
            return handle_update_code(cmd)
        elif action == "update_code_bulk":
            return handle_update_code_bulk(cmd)

        elif action == "append_file":
            with open(full_file_path, "a", encoding="utf-8") as f:
                f.write(content)
            save_to_memory(cmd)
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
                save_to_memory(cmd)
                return {"status": "success", "message": f"🔁 Updated file '{filename}'"}
            else:
                return {"status": "error", "message": "File not found"}

        elif action == "replace_in_file":
            if filename.endswith('.py'):
                test_result = handle_command({"action": "test_python", "filename": filename})
                if test_result.get("status") == "error":
                    return {"status": "error", "message": f"❌ Перед зміною: {test_result.get('message')}"}
                
                if not is_valid_python_file(full_file_path):
                    return {"status": "error", "message": f"❌ Syntax error before change in {filename}"}

            if filename in ["config.py", "api_keys.py", "cache.txt"]:
                    return {"status": "error", "message": f"❌ Заборонено змінювати критичний файл: {filename}"}
                
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                # 🧠 Зберігаємо резервну копію
                backup_path = full_file_path + ".bak"
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(text)
                    
                # 📝 Git diff перед записом
                try:
                    diff_output = subprocess.check_output(["git", "diff", full_file_path], cwd=base_path, text=True)
                    if diff_output.strip():
                        log_action("📄 Git diff перед зміною:" + diff_output)
                except Exception as e:
                    log_action(f"⚠️ Git diff error: {str(e)}")

                # 🔁 Заміна через regex
                new_text = re.sub(pattern, replacement, text)
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(new_text)
                
                if not is_valid_python_file(full_file_path):
                    return {"status": "error", "message": f"❌ Syntax error after change in {filename}. Revert or fix manually."}

                # 📜 Лог змін (git diff)
                log_diff(full_file_path)
                save_to_memory(cmd)
                return {"status": "success", "message": f"✏️ Replaced text in '{filename}'"}
            
        elif action == "insert_between_markers":
            file_path = os.path.join(base_path, cmd.get("file_path"))
            marker_start = cmd.get("marker_start")
            marker_end = cmd.get("marker_end")
            insert_code = cmd.get("code")

            if not all([file_path, marker_start, marker_end, insert_code]):
                return {"status": "error", "message": "❌ Missing required fields for marker-based insertion"}

            if not os.path.exists(file_path):
                return {"status": "error", "message": f"❌ File '{file_path}' not found"}

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            start_idx, end_idx = -1, -1
            for i, line in enumerate(lines):
                if marker_start in line:
                    start_idx = i + 1
                if marker_end in line:
                    end_idx = i

            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                return {"status": "error", "message": "❌ Markers not found or invalid order"}

            lines = lines[:start_idx] + [insert_code + "\n"] + lines[end_idx:]

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            save_to_memory(cmd)
            return {"status": "success", "message": f"✅ Inserted code between markers in {cmd.get('file_path')}"}
           
        elif action == "read_file":
            if os.path.exists(full_file_path):
                with open(full_file_path, "r", encoding="utf-8") as f:
                    return {"status": "success", "content": f.read()}
            save_to_memory(cmd)
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
                save_to_memory(cmd)
                return {"status": "success", "message": f"🗑️ File '{filename}' deleted"}
            else:
                return {"status": "error", "message": f"File '{filename}' not found"}

        elif action == "rename_file":
            if not os.path.exists(full_file_path):
                return {"status": "error", "message": f"❌ File '{filename}' not found"}
            new_path = os.path.join(base_path, new_name)
            os.rename(full_file_path, new_path)
            save_to_memory(cmd)
            return {"status": "success", "message": f"📄 File renamed to '{new_name}'"}

        elif action == "copy_file":
            shutil.copy(full_file_path, dst_file_path)
            save_to_memory(cmd)
            return {"status": "success", "message": f"📂 Copied '{filename}' to '{target_folder}'"}

        elif action == "read_folder":
            if os.path.exists(full_folder_path):
                files = os.listdir(full_folder_path)
                return {"status": "success", "files": files}
            return {"status": "error", "message": "Folder not found"}

        elif action == "run_python":
            if not os.path.exists(full_file_path):
                return {"status": "error", "message": f"❌ File '{filename}' not found"}
            result = subprocess.run(["python", full_file_path], capture_output=True, text=True)
            return {"status": "success", "output": result.stdout, "errors": result.stderr}
        
        elif action == "test_gpt_api":
            try:
                from openai import OpenAI
                from config import API_KEY
                client = OpenAI(api_key=API_KEY)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "user", "content": "Ping"}
                    ]
                )
                return {"status": "success", "message": "🟢 GPT API connected!", "response": response.choices[0].message.content}
            except Exception as e:
                return {"status": "error", "message": f"❌ GPT API error: {str(e)}"}


        elif action == "test_python":
            if os.path.exists(full_file_path):
                try:
                    with open(full_file_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    compile(source, filename, 'exec')
                    return {"status": "success", "message": f"✅ {filename} пройшов синтаксичну перевірку"}
                except SyntaxError as e:
                    return {"status": "error", "message": f"❌ Syntax error in {filename}: {e}"}
            return {"status": "error", "message": "File not found"}

        elif action == "undo_change":
            if os.path.exists(full_file_path + ".bak"):
                shutil.copy(full_file_path + ".bak", full_file_path)
                save_to_memory(cmd)
                return {"status": "success", "message": f"↩️ Undo: відкат до .bak для '{filename}'"}
            else:
                return {"status": "error", "message": f"❌ Немає резервної копії для '{filename}'"}

        elif action == "macro":
            return handle_macro(cmd)
        
        elif cmd["action"] == "run_shell":
            return handle_run_shell(cmd)

        elif action == "list_files":
            return {"status": "success", "files": os.listdir(base_path)}

        elif action == "check_status":
            return {"status": "success", "message": "🟢 Agent is running"}

        elif action == "show_memory":
            memory_file = os.path.join(base_path, ".ben_memory.json")
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                return {"status": "success", "memory": memory[-20:]}
            else:
                return {"status": "error", "message": "❌ Memory file not found"}
        
        elif action == "list_history":
            return handle_list_history()

        elif action == "view_sql_history":
            return get_history()

        else:
            return {"status": "error", "message": f"❌ Unknown action: {action}"}

        # 📝 Зберігаємо дію в SQLite
        try:
            import sqlite3
            conn = sqlite3.connect(os.path.join(base_path, "history.sqlite"))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO command_history (action, file_path, update_type)
                VALUES (?, ?, ?)
            """, (cmd.get("action"), cmd.get("file_path") or cmd.get("filename"), cmd.get("update_type")))
            conn.commit()
            conn.close()
        except Exception as e:
            log_action(f"⚠️ SQLite save error: {e}")


    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "message": f"❌ Exception: {str(e)}"}
def run_self_tests():
    print("\n🧪 Running self-tests...")
    tests_passed = 0
    tests_failed = 0

    # 1. Test basic command structure
    result = handle_command({"action": "check_status"})
    if result.get("status") == "success":
        print("✅ check_status passed")
        tests_passed += 1
    else:
        print("❌ check_status failed")
        tests_failed += 1

    # 2. Test missing required key
    result = handle_command({})
    if result.get("status") == "error" and "Missing required field" in result.get("message", ""):
        print("✅ missing field validation passed")
        tests_passed += 1
    else:
        print("❌ missing field validation failed")
        tests_failed += 1

    # 3. Test invalid command type
    result = handle_command("not_a_dict")
    if result.get("status") == "error" and "Invalid command format" in result.get("message", ""):
        print("✅ invalid format validation passed")
        tests_passed += 1
    else:
        print("❌ invalid format validation failed")
        tests_failed += 1

    # ✅ ПЕРЕНЕСЕНО СЮДИ:
    handle_command({"action": "delete_file", "filename": "test_self.txt"})

    result = handle_command({"action": "create_file", "filename": "test_self.txt", "content": "Hello test!"})
    if result.get("status") == "success":
        print("✅ create_file passed")
        tests_passed += 1
    else:
        print("❌ create_file failed")
        tests_failed += 1

    result = handle_command({"action": "read_file", "filename": "test_self.txt"})
    if result.get("status") == "success" and "Hello test!" in result.get("content", ""):
        print("✅ read_file passed")
        tests_passed += 1
    else:
        print("❌ read_file failed")
        tests_failed += 1

    result = handle_command({"action": "delete_file", "filename": "test_self.txt"})
    if result.get("status") == "success":
        print("✅ delete_file passed")
        tests_passed += 1
    else:
        print("❌ delete_file failed")
        tests_failed += 1

    # ✅ Тільки тепер — фінал
    print(f"\n🧪 Test results: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0
# 🧰 CLI-інтерфейс для ручного введення команд
import argparse

import argparse
import sys
import json

def run_cli():
    parser = argparse.ArgumentParser(description="Ben CLI")
    parser.add_argument("--action", help="Дія для виконання (наприклад, create_file)")
    parser.add_argument("--filename", help="Ім'я файлу")
    parser.add_argument("--content", help="Вміст для запису")
    parser.add_argument("--pattern", help="Патерн для пошуку")
    parser.add_argument("--replacement", help="Текст для заміни")
    parser.add_argument("--foldername", help="Ім'я папки")
    parser.add_argument("--target_folder", help="Цільова папка")
    parser.add_argument("--new_name", help="Нове ім'я файлу")
    parser.add_argument("--steps", help="JSON-рядок для macro-команди")

    args = parser.parse_args()

    print("Аргументи командного рядка:", sys.argv)  # Виводимо аргументи для перевірки

    cmd = {k: v for k, v in vars(args).items() if v is not None}

    # Перевірка і парсинг JSON для macro-команди
    if cmd.get("action") == "macro" and "steps" in cmd:
        try:
            cmd["steps"] = json.loads(cmd["steps"])  # Парсимо JSON
            print("Парсинг JSON успішний:", cmd["steps"])  # Перевірка парсингу
        except Exception as e:
            print(f"❌ Помилка парсингу steps: {str(e)}")
            return

    if "action" not in cmd:
        print("❌ Ви повинні вказати --action")
        return

    result = handle_command(cmd)
    print("🔧 Результат:", result)


def git_auto_push(commit_msg="🚀 Auto-commit by Ben"):
    try:
        subprocess.run(["git", "add", "."], cwd=base_path, check=True)

        # 🔍 Перевірка чи є зміни
        diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=base_path)
        if diff_result.returncode == 0:
            log_action("ℹ️ Немає змін для коміту — git push пропущено")
            return {"status": "skipped", "message": "ℹ️ No changes to commit"}

        subprocess.run(["git", "commit", "-m", commit_msg], cwd=base_path, check=True)
        subprocess.run(["git", "push"], cwd=base_path, check=True)
        log_action(f"📤 Git push: {commit_msg}")
        save_to_memory({"action": "git_push", "message": commit_msg})
        return {"status": "success", "message": "📤 Git push успішно завершено"}

    except subprocess.CalledProcessError as e:
        log_action(f"❌ Git push помилка: {str(e)}")
        return {"status": "error", "message": f"❌ Git push помилка: {str(e)}"}
def handle_update_code_bulk(command):
    updates = command.get('updates', [])
    results = []
    for update in updates:
        result = handle_update_code(update)
        results.append(result)
    return {"status": "success", "results": results}
   
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="GPT Agent CLI")
    parser.add_argument("--cli", action="store_true", help="Запустити CLI-режим")
    parser.add_argument("--test", action="store_true", help="Запустити self-тести")
    parser.add_argument("--action")
    parser.add_argument("--filename")
    parser.add_argument("--content")
    parser.add_argument("--pattern")
    parser.add_argument("--replacement")
    parser.add_argument("--foldername")
    parser.add_argument("--target_folder")
    parser.add_argument("--new_name")

    args = parser.parse_args()

    if args.test:
        run_self_tests()
        sys.exit()

    if args.cli:
        cmd = {k: v for k, v in vars(args).items() if v is not None and k not in ["cli", "test"]}
        if "action" not in cmd:
            print("❌ Ви повинні вказати --action")
            sys.exit(1)
        result = handle_command(cmd)
        print("🔧 Результат:", result)
        sys.exit()

    # Якщо не CLI і не test — запуск бота як звично
    print("🟢 Бен запущений і слухає команди з cache.txt...")
    while True:
        commands = read_requests()
        print("📩 Отримано команди:", commands)

        responses = []
        for cmd in commands:
            result = handle_command(cmd)
            print("✅ Виконано:", result)
            responses.append(result)
            log_action(result.get("message", str(result)))
            if result.get("status") == "success":
                push_result = git_auto_push(f"✅ Auto-commit: {cmd.get('action')} {cmd.get('filename', '')}")
                print(push_result.get('message', ''))

        if responses:
            for r in responses:
                status = r.get("status")
                if status == "success":
                    print(Fore.GREEN + "✅", r.get("message", "") + Style.RESET_ALL)
                elif status == "error":
                    print(Fore.RED + "❌", r.get("message", "") + Style.RESET_ALL)
                elif status == "cancelled":
                    print(Fore.YELLOW + "⚠️", r.get("message", "") + Style.RESET_ALL)
                elif status == "macro":
                    print(Fore.CYAN + "📦 Виконано macro-команду:" + Style.RESET_ALL)
                    for step_result in r.get("results", []):
                        print("  -", step_result.get("message", ""))

            print("💾 Записую gpt_response.json і очищаю cache.txt")
            write_response(responses)
            clear_cache()
        time.sleep(1)

def repeat_last_action():
    memory_file = os.path.join(base_path, ".ben_memory.json")
    if not os.path.exists(memory_file):
        return {"status": "error", "message": "❌ Memory file not found"}
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            memory = json.load(f)
        if not memory:
            return {"status": "error", "message": "❌ No memory to repeat"}
        last_cmd = memory[-1]
        save_to_memory(last_cmd)
        return handle_command(last_cmd)
    except Exception as e:
        return {"status": "error", "message": f"❌ Repeat error: {str(e)}"}


import autopep8
import os

# Крок 2: Функція для виправлення відступів
def fix_indentation(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            code = file.read()

        fixed_code = autopep8.fix_code(code)

        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(fixed_code)

        return {'status': 'success', 'message': f'🧹 Виправлені відступи в файлі {filepath}'}
    except Exception as e:
        return {'status': 'error', 'message': f'❌ Помилка виправлення відступів: {str(e)}'}

import sqlite3

# Створюємо підключення до бази даних SQLite
def create_connection():
    conn = sqlite3.connect('history.db')
    return conn

# Функція для збереження команди в історію
def save_to_history(action, filename, content, result):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO history (action, filename, content, result)
    VALUES (?, ?, ?, ?)
    ''', (action, filename, content, result))
    conn.commit()
    conn.close()

# Функція для отримання останніх записів з історії
def get_history():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history ORDER BY timestamp DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()
    return rows

def auto_commit(commit_msg="♻️ Rollback after failure"):
    try:
        subprocess.run(["git", "add", "."], cwd=base_path, check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=base_path, check=True)
        subprocess.run(["git", "push"], cwd=base_path, check=True)
        log_action(f"📤 Git auto-commit: {commit_msg}")
        save_to_memory({"action": "auto_commit", "message": commit_msg})
        return {"status": "success", "message": "📤 Git auto-commit завершено"}
    except subprocess.CalledProcessError as e:
        log_action(f"❌ Auto-commit помилка: {str(e)}")
        return {"status": "error", "message": f"❌ Auto-commit помилка: {str(e)}"}


# [BEN] Validation logic inserted here
def write_debug_log(message):
    with open(os.path.join(base_path, 'debug.log'), 'a', encoding='utf-8') as f:
        f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}\n')