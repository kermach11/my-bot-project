import os
import json
from colorama import init, Fore, Style
init()
import time
import re
import shutil
import subprocess
import traceback
from datetime import datetime, timezone

from config import base_path, request_file, response_file, history_file

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
    if not isinstance(cmd, dict):
        return {"status": "error", "message": "❌ Invalid command format — expected a JSON object"}

    # 🛡️ Захист: перевірка на дублювання при вставці функцій
    if cmd.get("action") == "append_file" and "def " in cmd.get("content", ""):
        func_name_match = re.search(r"def (\w+)\(", cmd.get("content", ""))
        if func_name_match:
            func_name = func_name_match.group(1)
            with open(os.path.join(base_path, cmd["filename"]), "r", encoding="utf-8") as f:
                if f"def {func_name}(" in f.read():
                    return {"status": "skipped", "message": f"⚠️ Function '{func_name}' already exists in {cmd['filename']}"}

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
                    
                # 📜 Лог змін (git diff)
                log_diff(full_file_path)
                save_to_memory(cmd)
                return {"status": "success", "message": f"✏️ Replaced text in '{filename}'"}
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
            if not isinstance(cmd.get("steps"), list):
                return {"status": "error", "message": "❌ Invalid macro steps"}
            results = []
            for step in cmd.get("steps", []):
                result = handle_command(step)
                results.append(result)
            return {"status": "success", "steps": results}

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

        else:
            return {"status": "error", "message": f"❌ Unknown action: {action}"}


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
    cmd = {k: v for k, v in vars(args).items() if v is not None}
    if cmd.get("action") == "macro" and "steps" in cmd:
        import json
        try:
            cmd["steps"] = json.loads(cmd["steps"])
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


import autopep8

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

# Крок 3: Інтеграція виправлення відступів перед виконанням заміни

def handle_command(cmd):
    try:
        action = cmd.get('action')
        filename = cmd.get('filename')
        full_file_path = os.path.join(base_path, filename) if filename else None

        if full_file_path:
            # Викликаємо fix_indentation перед виконанням заміни
            fix_result = fix_indentation(full_file_path)
            if fix_result['status'] == 'error':
                return fix_result  # Якщо є помилка в форматуванні, зупиняємо виконання

        # Далі виконуються інші дії, наприклад заміни
        if action == 'replace_in_file':
            # Ваш код заміни
            pass

        return {'status': 'success', 'message': 'Команда виконана успішно'}
    except Exception as e:
        return {'status': 'error', 'message': f'❌ Exception: {str(e)}'}