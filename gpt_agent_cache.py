def handle_command(cmd):
    # 🧠 Обробка підтвердження rollback
    if cmd.get("action") in ["yes", "no"] and cmd.get("target_id"):
        target_id = cmd["target_id"]
        if cmd["action"] == "yes":
            prev_cmd = get_command_by_id(target_id)
            if not prev_cmd:
                return {"status": "error", "message": f"❌ Не знайдено команду для відкату: {target_id}"}
            file_path = prev_cmd.get("file")
            if not file_path or not os.path.exists(file_path + ".bak"):
                return {"status": "error", "message": f"❌ Немає резервної копії для '{target_id}'"}
            shutil.copy(file_path + ".bak", file_path)
            return {"status": "success", "message": f"✅ Відкат завершено для {target_id}"}
        else:
            return {"status": "cancelled", "message": f"⛔ Відкат скасовано для {target_id}"}

    if cmd.get("filename") == "env" or cmd.get("file_path", "").endswith("env"):
        if cmd["action"] in ["update_file", "append_file", "replace_in_file", "update_code", "delete_file"]:
            return {"status": "error", "message": "❌ Заборонено змінювати або комітити файл 'env'"}

import os
import sys
import json
import time
import re
import ast
import shutil
import subprocess
import traceback
import sqlite3
from datetime import datetime, timezone
from colorama import init, Fore, Style
from dotenv import load_dotenv

init()

# 🧠 Завантаження змінних середовища
load_dotenv("C:/Users/DC/env_files/env")

# 🧩 Додавання base_path до sys.path для імпорту
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

# ⚙️ Імпорт конфігурації
from config import base_path, request_file, response_file, history_file, API_KEY

# 🧠 GPT-інтерпретація
from gpt_interpreter import interpret_user_prompt
interpret_user_prompt("створи функцію, яка перевіряє, чи пароль має щонайменше 8 символів")

def backup_file(filepath):
    if not filepath or not os.path.isfile(filepath):
        print(f"⚠️ Пропущено backup — некоректний шлях: {filepath}")
        return

    # Формуємо безпечну резервну копію з .bak
    bak_path = filepath + ".bak"
    if not os.path.exists(bak_path):
        try:
            shutil.copy2(filepath, bak_path)
            print(f"📦 Створено резервну копію: {bak_path}")
        except Exception as e:
            print(f"❌ Помилка резервування: {e}")

import re

def substitute_arguments(command_str, arguments):
    if not arguments:
        return command_str
    for key, value in arguments.items():
        command_str = command_str.replace(f"{{{{{key}}}}}", str(value))
    return command_str

def execute_macro(macro_name, arguments=None):
    macro_file = os.path.join(base_path, "macro_commands.json")
    if not os.path.isfile(macro_file):
        return {"status": "error", "message": "❌ macro_commands.json not found"}

    with open(macro_file, "r", encoding="utf-8") as f:
        macros = json.load(f)

    # 🔄 Пошук макросу по імені
    macro_steps = None
    for macro in macros:
        if macro.get("macro_name") == macro_name:
            macro_steps = macro.get("steps")
            break

    if not macro_steps:
        return {"status": "error", "message": f"❌ Невідома макрокоманда: {macro_name}"}

    for step in macro_steps:
        if isinstance(step, dict):
            if "action" in step:
                # 🟢 Плоский формат: { "action": "...", "filename": "...", ... }
                action = step["action"]
                params = {k: v for k, v in step.items() if k != "action"}
            else:
                # 🔵 Класичний формат: { "replace_in_file": { ... } }
                action, params = next(iter(step.items()))
        else:
            print("⚠️ Невірний формат кроку макросу, пропускаю...")
            continue

        if action == "run_shell":
            command = substitute_arguments(params["command"], arguments)
            result = os.popen(command).read().strip()
            print(result)
        else:
            # Вставка виконання стандартних дій (replace, append, update_code, тощо)
            response = handle_command({ "action": action, **params })
            print(response.get("message", f"✅ {action} виконано"))

    return {"status": "success", "message": f"✅ Макрос '{macro_name}' виконано"}

import shutil

def undo_last_backup(filepath):
    backups = [f for f in os.listdir(base_path) if f.startswith(os.path.basename(filepath)) and ".backup_" in f]
    backups.sort(reverse=True)
    if backups:
        last_backup = os.path.join(base_path, backups[0])
        shutil.copy2(last_backup, filepath)
        return {"status": "success", "message": f"✅ Restored from backup: {last_backup}"}
    return {"status": "error", "message": "❌ No backup found"}

import subprocess

def write_debug_log(message):
    debug_log_path = os.path.join(base_path, "debug.log")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(debug_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def generate_macro_steps_from_prompt(prompt_text):
    from openai import OpenAI
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
            {"role": "user", "content": prompt_text}
        ]
    )

    try:
        steps = json.loads(response.choices[0].message.content.strip())
        return {"status": "success", "steps": steps}
    except Exception as e:
        return {"status": "error", "message": f"❌ Не вдалося згенерувати кроки: {e}"}

def self_improve_agent(filename="gpt_agent_cache.py"):
    try:
        filepath = os.path.join(base_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()

        prompt = f"""
🔍 Ти GPT-агент, який аналізує свій власний код.  
Файл: `{filename}`  
Ось його вміст:

{code}

🧠 Визнач, які мікропокращення можна внести: оптимізації, спрощення, додавання перевірок або чистого рефакторингу.

⚙️ Згенеруй Python-JSON обʼєкт із дією `safe_update_code`, у форматі:

{{
  "action": "safe_update_code",
  "filename": "{filename}",
  "updates": [
    {{
      "pattern": "REGEX-ПАТЕРН",
      "replacement": "НОВИЙ КОД",
      "update_type": "replace"
    }}
  ]
}}

Поверни тільки об'єкт JSON, без пояснень.
"""

        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content.strip())

        # 💾 Зберігаємо результат для попереднього перегляду
        with open("gpt_response.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # ⛑️ Автоматичне safe update
        update_result = handle_safe_update_code(result, base_path)
        return update_result

    except Exception as e:
        return {"status": "error", "message": f"❌ Self-improvement failed: {e}"}
def generate_improvement_plan():
    try:
        # 1. Отримати всі .py файли
        files = scan_all_files(base_path, [".py"])
        file_snippets = []

        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    file_snippets.append({"file": path, "code": content[:2000]})  # до 2k символів
            except:
                continue

        # 2. GPT prompt
        prompt = f"""
📁 У мене є Python-проєкт із такими файлами:
{json.dumps(file_snippets, indent=2, ensure_ascii=False)}

🧠 Згенеруй покращення для цього проєкту — список macro-кроків для рефакторингу, оптимізації, захисту або нового функціоналу.

Поверни тільки JSON у форматі:

{{
  "action": "run_macro",
  "steps": [ ... ]
}}
"""

        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        plan = json.loads(response.choices[0].message.content.strip())

        # 💾 Зберігаємо в gpt_plan.json
        with open("gpt_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)

        return {"status": "success", "message": "📋 План збережено в gpt_plan.json", "steps": plan.get("steps", [])}

    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка Smart-планувальника: {e}"}

def analyze_all_code():
    try:
        files = scan_all_files(base_path, [".py"])
        file_snippets = []

        for path in files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    file_snippets.append({"file": path, "code": content[:2000]})
            except:
                continue

        prompt = f"""
📁 Проаналізуй якість наступного Python-коду.  
Перевір: дублікати функцій, відсутність логування, неефективні місця, погане структурування.

Файли:
{json.dumps(file_snippets, indent=2, ensure_ascii=False)}

🧠 Поверни детальний звіт у форматі:
{{
  "status": "ok",
  "recommendations": [ ... ]
}}
"""

        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)

        # Спроба максимум 2 рази, якщо JSON невалідний
        for attempt in range(2):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.choices[0].message.content.strip()

            # 💾 Зберігаємо RAW-вивід для діагностики
            with open("gpt_analysis_raw.txt", "w", encoding="utf-8") as f:
                f.write(raw)

            try:
                report = json.loads(raw)
                break  # ✅ JSON валідний, виходимо
            except json.JSONDecodeError as e:
                print(f"⚠️ Спроба {attempt + 1} — помилка JSON: {e}")
                if attempt == 1:
                    return {"status": "error", "message": f"❌ GPT не повернув валідний JSON: {e}"}

        # 💾 Зберігаємо у звіт
        with open("gpt_analysis.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return {"status": "success", "message": "📊 Аналіз збережено в gpt_analysis.json"}

    except Exception as e:
        return {"status": "error", "message": f"❌ Analyze failed: {e}"}

def execute_plan():
    plan_file = os.path.join(base_path, "gpt_plan.json")
    if not os.path.exists(plan_file):
        return {"status": "error", "message": "❌ gpt_plan.json не знайдено"}

    try:
        with open(plan_file, "r", encoding="utf-8") as f:
            plan = json.load(f)

        if not isinstance(plan, list):
            return {"status": "error", "message": "❌ gpt_plan.json має бути списком дій"}

        results = []
        for i, step in enumerate(plan):
            print(f"\n⚙️ Виконую крок {i + 1}/{len(plan)}: {step.get('action')}")
            result = handle_command(step)
            results.append(result)

            if result.get("status") != "success":
                print(f"❌ Зупинено на кроці {i + 1} — помилка: {result.get('message')}")
                return {
                    "status": "error",
                    "message": f"❌ План зупинено на кроці {i + 1}",
                    "results": results
                }

        return {
            "status": "success",
            "message": f"✅ План виконано повністю ({len(plan)} кроків)",
            "results": results
        }

    except Exception as e:
        return {"status": "error", "message": f"❌ execute_plan помилка: {e}"}

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
def get_command_by_id(target_id):
    try:
        with open(".ben_memory.json", "r", encoding="utf-8") as f:
            memory = json.load(f)
        for entry in reversed(memory):  # Останні першими
            if entry.get("history_id") == target_id:
                return entry
    except:
        pass
    return None
def ask_confirmation_for_rollback(prev_code, target_id):
    prompt = (
        f"🧠 Знайдено код, який буде відновлено з ID {target_id}:\n\n"
        f"{prev_code}\n\n"
        "🔁 Хочеш відкотити до цього коду? Напиши 'yes' або 'no'"
    )
    with open("gpt_response.json", "w", encoding="utf-8") as f:
        json.dump({"status": "awaiting_confirmation", "message": prompt, "target_id": target_id}, f, indent=2, ensure_ascii=False)
    return {"status": "paused", "message": "⏸️ Очікуємо підтвердження на відкат"}

import importlib.util
import shutil

CRITICAL_FILES = [
    "gpt_agent_cache.py",
    "ben_writer.py",
    "cache.txt",
    "gpt_response.json",
    "macro_commands.json"
]

def handle_safe_update_code(cmd, base_path):
    filename = cmd.get("filename")
    updates = cmd.get("updates", [])
    filepath = os.path.join(base_path, filename)

    if not os.path.exists(filepath):
        return {"status": "error", "message": f"❌ File not found: {filename}"}

    # 🔧 Додаємо base_path у sys.path
    import sys
    if base_path not in sys.path:
        sys.path.append(base_path)

    # 1. Create backup
    backup_path = filepath + ".bak"
    shutil.copyfile(filepath, backup_path)

    # 2. Read original
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Apply updates
    try:
        for update in updates:
            pattern = update["pattern"]
            replacement = update["replacement"]
            multiple = update.get("multiple", False)
            flags = re.MULTILINE | re.DOTALL
            if multiple:
                content = re.sub(pattern, replacement, content, flags=flags)
            else:
                content = re.sub(pattern, replacement, content, count=1, flags=flags)
    except Exception as e:
        return {"status": "error", "message": f"❌ Regex error: {str(e)}"}

    # 4. Write to temp
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 5. Синтаксична перевірка через ast
    if filename.endswith(".py"):
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                code = f.read()
                ast.parse(code)  # 🛡️ Перевірка на синтаксичну валідність
        except Exception as e:
            return {"status": "error", "message": f"❌ Syntax error: {str(e)}. Rolled back."}

        # 6. (опціонально) Повна перевірка імпорту
        try:
            spec = importlib.util.spec_from_file_location("tmp_module", tmp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
        except Exception as e:
            return {"status": "error", "message": f"❌ Import error: {str(e)}. Rolled back."}


    # 7. All good — apply
    shutil.move(tmp_path, filepath)
    return {"status": "success", "message": f"✅ Safe update applied to {filename}"}

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

def handle_check_file_access(filename):
    filepath = os.path.join(base_path, filename)
    if os.path.isfile(filepath):
        return {"status": "success", "message": "✅ File exists"}
    else:
        return {"status": "error", "message": f"❌ File not found: {filename}"}

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

    # 🛡️ Захищені файли
    protected_files = ["gpt_agent_cache.py", "cache.txt", "ben_gui_v2.py"]
    filename = os.path.basename(file_path)
    if filename in protected_files:
        return {"status": "error", "message": f"❌ Cannot modify protected file: {filename}"}
    
    # ✅ Бекап перед змінами
    if file_path and os.path.exists(file_path):
        backup_file(file_path)

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

def handle_analyze_json(cmd, base_path="."):
    filename = cmd.get("filename")
    if not filename:
        return {"status": "error", "message": "❌ Не вказано 'filename'"}
    
    filepath = os.path.join(base_path, filename)
    if not os.path.exists(filepath):
        return {"status": "error", "message": f"❌ Файл не знайдено: {filepath}"}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        data = json.loads(content)  # валідність
    except Exception as e:
        return {"status": "error", "message": f"❌ JSON помилка: {e}"}
    
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
Проаналізуй наступний JSON і дай поради:
- чи добре структуровано?
- що можна покращити?
- чи є логічні проблеми?

Ось JSON:
{json.dumps(data, indent=2, ensure_ascii=False)}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content.strip()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = f"gpt_json_analysis_{timestamp}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(reply)

    return {"status": "success", "message": f"📄 Збережено аналіз у {out_path}"}


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
            filepath = cmd.get("file_path") or cmd.get("file")
            if not filepath:
                return {"status": "error", "message": "❌ Missing 'file_path'"}

            full_path = os.path.join(base_path, filepath)
            if not os.path.isfile(full_path):
                return {"status": "error", "message": f"❌ File not found: {filepath}"}

            updates = cmd.get("updates", [])
            if not updates:
                return {"status": "error", "message": "❌ No updates provided"}

            result = apply_updates_to_file(full_path, updates)

            # 🧪 Автотест після оновлення
            test_result = handle_command({
                "action": "test_python",
                "filename": filepath
            })
            print(f"🧪 Результат автотесту: {test_result}")

            return {"status": "success", "message": f"✅ Updated {filepath}", "details": result}
      
        elif action == "safe_update_code":
            result = handle_safe_update_code(cmd, base_path)

            # 🧠 Додано захист, щоб уникнути .get() помилки
            if result is None:
                result = {"status": "error", "message": "❌ handle_safe_update_code не повернув результат"}

            return result

        elif action == "update_code_bulk":
            return handle_update_code_bulk(cmd)

        elif action == "append_file":
            filename = cmd["filename"]
            content = cmd["content"]
            filepath = os.path.join(base_path, filename)
            backup_file(filepath)

            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content)

            save_to_memory(cmd)

            # 🧪 Автоматична перевірка коду після вставки
            test_result = handle_command({
                "action": "test_python",
                "filename": filename
            })
            print(f"🧪 Результат автотесту: {test_result}")

            return {"status": "success", "message": f"📌 Appended to file '{filename}'"}

        
        elif action == "undo_change":
            ilename = cmd.get("filename")
            result = undo_last_backup(os.path.join(base_path, filename))
            results.append(result)

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
            filename = cmd["filename"]
            pattern = cmd["pattern"]
            replacement = cmd["replacement"]
            filepath = os.path.join(base_path, filename)
            full_file_path = filepath

            backup_file(filepath)

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

                # 📜 Лог змін
                log_diff(full_file_path)
                save_to_memory(cmd)

                # 🧪 Автотест після зміни
                test_result = handle_command({
                    "action": "test_python",
                    "filename": filename
                })
                print(f"🧪 Результат автотесту: {test_result}")

                return {"status": "success", "message": f"✏️ Replaced text in '{filename}'"}

            
        elif action == "insert_between_markers":
            filepath = os.path.join(base_path, cmd["filename"])
            backup_file(filepath)
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
            filepath = os.path.join(base_path, cmd["filename"])
            backup_file(filepath)
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
        
        elif action == "self_improve":
            filename = cmd.get("filename", "gpt_agent_cache.py")
            result = self_improve_agent(filename)
            return result
        
        elif action == "smart_plan":
             result = generate_improvement_plan()
             return result
        
        elif action == "run_plan":
             return execute_plan()

        elif action == "analyze_all_code":
            result = analyze_all_code()
            return result
        
        elif action == "analyze_json":
             return handle_analyze_json(cmd, base_path)

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
            target_id = cmd.get("target_id")

            if target_id:
                # 🔍 Шукаємо команду по ID з історії
                prev_cmd = get_command_by_id(target_id)
                if not prev_cmd:
                    return {"status": "error", "message": f"❌ Не знайдено команду з ID: {target_id}"}

                file_path = prev_cmd.get("file")
                if not file_path or not os.path.exists(file_path + ".bak"):
                    return {"status": "error", "message": f"❌ Немає резервної копії для ID: {target_id}"}

                with open(file_path + ".bak", "r", encoding="utf-8") as f:
                    prev_code = f.read()

                return ask_confirmation_for_rollback(prev_code, target_id)

            else:
                # 🕗 Стара логіка .bak
                if os.path.exists(full_file_path + ".bak"):
                    shutil.copy(full_file_path + ".bak", full_file_path)
                    save_to_memory(cmd)
                    return {"status": "success", "message": f"↩️ Undo: відкат до .bak для '{filename}'"}
                else:
                    return {"status": "error", "message": f"❌ Немає резервної копії для '{filename}'"}

        elif action == "macro":
            return handle_macro(cmd)
        
        elif cmd.get("action") == "check_file_access":
            filename = cmd.get("filename")
            return handle_check_file_access(filename)

        elif action == "run_macro":
            macro_name = cmd.get("macro_name")
            arguments = cmd.get("arguments", {})
            if not macro_name:
                return {"status": "error", "message": "❌ No macro_name provided"}
            return execute_macro(macro_name, arguments)

        elif action == "check_file_access":
            filename = cmd.get("filename")
            if filename:
                filepath = os.path.join(base_path, filename)
                if os.path.exists(filepath):
                    result = f"✅ File exists: {filename}"
                else:
                    result = f"❌ File not found: {filename}"
            else:
                result = "❌ No filename provided"
            print(result)
            return {"status": "success", "message": result}

        elif action == "execute_macro":
            macro_name = cmd.get("macro_name")
            arguments = cmd.get("arguments", {})
            return execute_macro(macro_name, arguments)
        
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
        
        elif action == "safe_update":
            result = handle_safe_update_code(cmd, base_path)
            results.append(result)

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

        # 🛠️ Спроба автодебагу при синтаксичній помилці
        if "Syntax error" in str(e):
            filepath = os.path.join(base_path, cmd.get("filename") or cmd.get("file_path", ""))
            auto_result = attempt_autodebug(filepath, str(e))
            return auto_result

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

def scan_all_files(folder, extensions=None):
    matched_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if not extensions or any(file.endswith(ext) for ext in extensions):
                matched_files.append(os.path.join(root, file))
    return matched_files
   
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

    try:
        from macros import run_macro
        auto = run_macro({"name": "scan_all_on_start"})
        print(f"[AUTO] {auto.get('message')}")
    except Exception as e:
        print(f"[AUTO] ❌ Помилка автозапуску: {e}")

    while True:
        commands = read_requests()
        print("📩 Отримано команди:", commands)

        responses = []
        for cmd in commands:
            result = handle_command(cmd)
            print("✅ Виконано:", result)
            responses.append(result)
            if isinstance(result, dict):
                log_action(result.get("message", str(result)))
            else:
                log_action(str(result))

            if isinstance(result, dict) and result.get("status") == "success":
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
    
def attempt_autodebug(filepath, error_message):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            faulty_code = f.read()

        prompt = f"""
🔍 У коді нижче виникла помилка під час виконання або компіляції:

❌ Помилка:
{error_message}

📄 Код:
{faulty_code}

🎯 Виправ, будь ласка, код так, щоб помилка зникла. Поверни лише виправлений код, без пояснень.
"""

        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        fixed_code = response.choices[0].message.content.strip()

        backup_file(filepath)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        write_debug_log("🔁 Автовиправлення застосовано GPT")
        return {"status": "success", "message": "✅ Автовиправлення застосовано"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Автовиправлення не вдалося: {e}"}

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