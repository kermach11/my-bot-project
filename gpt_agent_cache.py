
import os
import sys
sys.path.append(os.path.abspath("."))
import json
import time
import re
import ast
import shutil
import subprocess
import openai
import traceback
import sqlite3
from datetime import datetime, timezone
autopilot_mode = True
base_path = os.path.abspath(".")


# Інші глобальні змінні, функції...

from colorama import init as colorama_init, Fore, Style
colorama_init()
from dotenv import load_dotenv
from init_history_db import create_history_table
from handlers.file_creation import handle_create_file, handle_create_and_finalize_script
from handlers.memory_manager import is_forbidden_action, remember_phrase, forget_phrase
from handlers.auto_guess import auto_guess_missing_parameters
from utils.json_tools import clean_json_text
from utils.log_utils import log_action

# 🧠 Завантаження змінних середовища (з перевіркою)
env_path = "C:/Users/DC/env_files/env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print(Fore.YELLOW + f"⚠️ Файл .env не знайдено: {env_path}" + Style.RESET_ALL)

# 🧱 Створення таблиці історії команд
create_history_table()

# 🧠 Завантаження змінних середовища
load_dotenv("C:/Users/DC/env_files/env")

# 🧩 Додавання base_path до sys.path для імпорту
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

# 🧠 Ben cognitive layer — завантаження памʼяті
BEN_MEMORY_PATH = 'ben_memory.json'
ben_ego = {}
if os.path.exists(BEN_MEMORY_PATH):
    with open(BEN_MEMORY_PATH, 'r', encoding='utf-8') as f:
        ben_ego = json.load(f)
else:
    ben_ego = {"error": "❌ Памʼять Ben відсутня"}

def apply_ben_cognition_cycle(action_data):
    print("\n🧠 [Ben думає] Хто я:", ben_ego.get("identity", {}).get("name", "невідомо"))
    print("🎯 Мета:", ben_ego.get("mission", "немає місії"))
    print("📘 Стратегія:", ben_ego.get("vision", {}).get("strategy", []))
    print("🔍 Аналіз дії:", action_data)
    return action_data

def unwrap_parameters_if_present(command):
    if isinstance(command.get("parameters"), dict):
        command.update(command["parameters"])
        del command["parameters"]
    return command

def handle_command(cmd):
    cmd = apply_ben_cognition_cycle(cmd)  # 🧠 свідомість Ben
    cmd = unwrap_parameters_if_present(cmd)
    create_history_table()

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

def apply_updates_to_file(file_path, updates):
    import re

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for update in updates:
        pattern_str = update.get('pattern')
        replacement = update.get('replacement', '')
        multiple = update.get('multiple', False)

        if not pattern_str or not isinstance(pattern_str, str):
            return {"status": "error", "message": "❌ Невірний або порожній pattern"}

        try:
            pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE)
        except re.error as e:
            return {"status": "error", "message": f"❌ Некоректний regex: {e}"}

        count = 0 if multiple else 1
        content = pattern.sub(replacement, content, count=count)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return {"status": "success", "message": f"✅ Applied updates to {file_path}"}


# ⚙️ Імпорт конфігурації
from config import base_path, request_file, response_file, history_file, API_KEY
import sqlite3


def create_history_table():
    conn = sqlite3.connect(os.path.join(base_path, "history.sqlite"))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO command_history (action, file_path, update_type, context_guide) VALUES (?, ?, ?, ?)", (
    cmd.get("action"),
    cmd.get("file_path") or cmd.get("filename"),
    cmd.get("update_type"),
    cmd.get("context_guide", "")
))
    ''')
    conn.commit()
    conn.close()

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
                action = step["action"]
                params = {k: substitute_arguments(v, arguments) if isinstance(v, str) else v for k, v in step.items() if k != "action"}
            else:
                action, raw_params = next(iter(step.items()))
                params = {k: substitute_arguments(v, arguments) if isinstance(v, str) else v for k, v in raw_params.items()}
        else:
            print("⚠️ Невірний формат кроку макросу, пропускаю...")
            continue

        if action == "run_shell":
            try:
                result = subprocess.run(params["command"], shell=True, capture_output=True, text=True)
                print(result.stdout.strip())
            except Exception as e:
                print(f"❌ Shell помилка: {e}")
        else:
            response = handle_command({"action": action, **params})
            print(response.get("message", f"✅ {action} виконано"))

    return {"status": "success", "message": f"✅ Макрос '{macro_name}' виконано"}

def run_macro():
    try:
        with open("macro_command.json", "r", encoding="utf-8") as f:
            macro = json.load(f)
        steps = macro.get("steps", [])
        for step in steps:
            print(f"📤 Крок: {step.get('action', '...')} надіслано")
            result = handle_command(step)
            print("✅ Виконано:", result)
        return {"status": "success", "message": "✅ Макрос виконано"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Макрос помилка: {e}"}

def undo_last_backup(filepath):
    backups = [f for f in os.listdir(base_path) if f.startswith(os.path.basename(filepath)) and ".backup_" in f]
    backups.sort(reverse=True)
    if backups:
        last_backup = os.path.join(base_path, backups[0])
        shutil.copy2(last_backup, filepath)
        return {"status": "success", "message": f"✅ Restored from backup: {last_backup}"}
    return {"status": "error", "message": "❌ No backup found"}

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
        model="gpt-3.5-turbo",
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
  ""action": "safe_update_code",
  "file_path": "{filename}",
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
            model="gpt-3.5-turbo",
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
            model="gpt-3.5-turbo",
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
                model="gpt-3.5-turbo",
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

    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return {"status": "error", "message": f"❌ Файл не знайдено або це не файл: {filename}"}

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
            pattern = update.get("pattern", "")
            if not pattern.strip():
                return {"status": "error", "message": "❌ Порожній regex pattern — зміни скасовано."}
            try:
                re.compile(pattern)
            except re.error as regex_error:
                return {"status": "error", "message": f"❌ Некоректний regex pattern: {regex_error}"}

            replacement = update.get("replacement", "")
            multiple = update.get("multiple", False)

            if not pattern.strip():
                return {"status": "error", "message": "❌ Пропущено — pattern не вказано або порожній"}

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

def handle_adaptive_safe_update_code(cmd, base_path):
    try:
        file_path = cmd.get("file_path")
        updates = cmd.get("updates", [])
        full_path = os.path.join(base_path, file_path)

        if not os.path.exists(full_path):
            return {"status": "error", "message": f"❌ Файл '{file_path}' не знайдено"}

        with open(full_path, "r", encoding="utf-8") as f:
            code = f.read()

        success_count = 0
        for update in updates:
            pattern = update.get("pattern")
            replacement = update.get("replacement")

            # Адаптивна перевірка — щоб не зламати структуру
            if re.search(pattern, code, re.MULTILINE):
                code = re.sub(pattern, replacement, code, flags=re.MULTILINE)
                success_count += 1
            else:
                print(f"⚠️ adaptive_safe_update_code: pattern не знайдено — {pattern}")

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)

        return {"status": "success", "message": f"✅ Застосовано {success_count} оновлень у {file_path}"}

    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка в adaptive_safe_update_code: {e}"}
    
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

from utils.json_tools import clean_json_text

def read_requests():
    if not os.path.exists(request_file):
        return []
    with open(request_file, "r", encoding="utf-8") as f:
        try:
            text = f.read().strip()
            if not text:
                return []
            text = clean_json_text(text)
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
    import os
    import json
    from datetime import datetime
    from openai import OpenAI

    # Уніфіковане витягування
    json_data = cmd.get("parameters", {}).get("json_data")
    filename = (
        cmd.get("filename")
        or cmd.get("parameters", {}).get("filename")
        or cmd.get("parameters", {}).get("file_path")
    )

    if json_data:
        data = json_data  # напряму переданий JSON
    elif filename:
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return {"status": "error", "message": f"❌ Файл не знайдено або це не файл: {filename}"}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"❌ JSON помилка: {e}"}
    else:
        return {"status": "error", "message": "❌ Не вказано 'filename', 'file_path' або 'json_data'"}

    # GPT-аналіз
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
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = response.choices[0].message.content.strip()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = f"gpt_json_analysis_{timestamp}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(reply)

    return {"status": "success", "message": f"📄 Збережено аналіз у {out_path}"}

def handle_summarize_file(cmd, base_path="."):
    import os
    import openai

    filename = (
        cmd.get("filename")
        or cmd.get("parameters", {}).get("filename")
        or cmd.get("parameters", {}).get("file_path")
    )

    # 🛡️ Виправлення — використовуємо дефолт, якщо шлях некоректний або файл не існує
    if not filename or filename == "unknown" or not os.path.exists(os.path.join(base_path, filename)):
        filename = "recent_actions.log"

    file_path = os.path.join(base_path, filename)
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"❌ Файл '{filename}' не знайдено"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка читання: {e}"}

    prompt = f"""
Зроби короткий підсумок наступного файлу. Вкажи:
1. Що міститься в ньому?
2. Яка основна логіка або структура?
3. Чи є потенційні покращення?

Ось вміст файлу `{filename}`:
{content[:3000]}  # обмежимо обсяг
"""

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content.strip()

    out_file = f"summarized_{filename}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(reply)

    return {"status": "success", "message": f"📄 Підсумок збережено у {out_file}"}

from handlers.memory_manager import remember_phrase

def handle_validate_shell_command(cmd, base_path="."):
    command = (
        cmd.get("parameters", {}).get("command")
        or cmd.get("command")
    )

    if command and isinstance(command, str) and len(command.strip()) > 3:
        remember_phrase(command.strip())

    if not command:
        return {"status": "error", "message": "❌ Не вказано команду для перевірки."}

    dangerous_keywords = ["rm", "shutdown", "reboot", "sudo", "mkfs", ":(){", ">:(", "dd if=", "kill -9"]
    if any(danger in command for danger in dangerous_keywords):
        return {
            "status": "error",
            "message": f"⚠️ Виявлено потенційно небезпечну команду: '{command}'"
        }

    return {
        "status": "ok",
        "message": f"✅ Shell-команда '{command}' виглядає безпечно."
    }

def handle_add_function(cmd, base_path="."):
    import os
    import ast

    filename = cmd.get("file") or cmd.get("parameters", {}).get("file")
    function_name = cmd.get("function_name") or cmd.get("parameters", {}).get("function_name")
    function_code = cmd.get("function_code") or cmd.get("parameters", {}).get("function_code")

    if not filename or not function_name or not function_code:
        return {"status": "error", "message": "❌ Не вказано файл, назву або код функції."}

    file_path = os.path.join(base_path, filename)

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        parsed = ast.parse(source)
        for node in parsed.body:
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return {
                    "status": "skipped",
                    "message": f"⚠️ Функція '{function_name}' вже існує у файлі '{filename}'"
                }

        with open(file_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + function_code.strip() + "\n")

        return {
            "status": "success",
            "message": f"✅ Функцію '{function_name}' додано до '{filename}'"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Помилка при додаванні функції: {str(e)}"
        }

from handlers.memory_manager import remember_phrase

def try_remember_dialogue(cmd):
    fields = [
        cmd.get("comment"),
        cmd.get("parameters", {}).get("prompt"),
        cmd.get("parameters", {}).get("query"),
        cmd.get("parameters", {}).get("text")
    ]
    for phrase in fields:
        if phrase and isinstance(phrase, str) and len(phrase.strip()) > 3:
            remember_phrase(phrase.strip())


def handle_command(cmd):
    cmd = apply_ben_cognition_cycle(cmd)  # 🧠 свідомість Ben

    # 🧠 Зберегти історію мислення
    with open("ben_thoughts_log.txt", "a", encoding="utf-8") as log:
        log.write(f"\n==== {datetime.now().isoformat()} ====\n")
        log.write(f"Identity: {ben_ego.get('identity', {}).get('name', 'невідомо')}\n")
        log.write(f"Mission: {ben_ego.get('mission', 'немає місії')}\n")
        log.write(f"Strategy: {ben_ego.get('vision', {}).get('strategy', [])}\n")
        log.write(f"Action Analyzed: {json.dumps(cmd, ensure_ascii=False, indent=2)}\n")

    cmd = unwrap_parameters_if_present(cmd)

    print("🧪 DEBUG — початкова команда:", cmd)

    if not isinstance(cmd, dict):
        return {"status": "error", "message": "❌ Invalid command format — expected a JSON object"}

    print("📦 DEBUG — parameters:", cmd.get("parameters", {}))

    # ❌ Перевірка заборонених дій з long_term_memory.json
    from handlers.memory_manager import is_forbidden_action
    if is_forbidden_action(cmd):
        return {
            "status": "error",
            "message": f"🚫 Ця дія заборонена відповідно до побажань користувача"
        }

    if not isinstance(cmd, dict):
        return {"status": "error", "message": "❌ Invalid command format — expected a JSON object"}
    # 🧩 Поправляємо параметри, якщо GPT зробив їх списком замість словника

    if isinstance(cmd.get("parameters"), list):
        print("⚠️ GPT повернув parameters у вигляді списку. Виправляю формат...")
        new_params = {}
        if "function_name" in cmd:
            new_params["name"] = cmd["function_name"]
        if "code" in cmd:
            new_params["code"] = cmd["code"]
        if "file_path" in cmd:
            new_params["file_path"] = cmd["file_path"]
        else:
            new_params["file_path"] = "example.py"
        cmd["parameters"] = new_params

    # 🧠 Автоматичне розпізнавання побажань у коментарях/промптах
    cmd = auto_guess_missing_parameters(cmd)
    
    if "file_path" in cmd.get("parameters", {}):
        fp = cmd["parameters"]["file_path"]
        if not os.path.exists(fp):
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                f.write("# 🆕 Автоматично створений файл\n")
            print(f"📁 Автоматично створено файл: {fp}")
   
    user_text = (
        cmd.get("comment") or
        cmd.get("parameters", {}).get("prompt") or
        cmd.get("parameters", {}).get("query") or
        ""
    ).lower()

    if "пам" in user_text or "запам" in user_text:
        phrase = user_text.strip()
        remember_phrase(phrase)

    if "не роби" in user_text or "заборон" in user_text:
        phrase = user_text.strip()
        forget_phrase(phrase)

    action = cmd.get("action")

    # ✅ Перевірка наявності обовʼязкових полів перед виконанням
    required_fields = {
        "add_function": ["file_path", "function_name", "code"],
        "append_file": ["filename", "content"],
        "update_code": ["file_path", "updates"],
        "safe_update_code": ["file_path", "updates"],
        "adaptive_safe_update_code": ["file_path", "updates"],
    }

    if action in required_fields:
        missing = [f for f in required_fields[action] if not cmd.get(f)]
        if missing:
            return {
                "status": "error",
                "message": f"❌ Помилка: команда '{action}' не має обов’язкових полів: {', '.join(missing)}. Будь ласка, надай повні дані для виконання дії."
            }


    # ✅ Відразу обробка відомих внутрішніх дій
    if action == "ask_gpt":
        from gpt_interpreter import interpret_user_prompt
        inner_prompt = (
            cmd.get("prompt")
            or cmd.get("parameters", {}).get("prompt")
            or ""
        )
        if inner_prompt.strip():
            answer = interpret_user_prompt(inner_prompt, return_data=False)
            try_remember_dialogue(cmd)
            return {"status": "ok", "message": answer}
        else:
            try_remember_dialogue(cmd)
            return {"status": "error", "message": "❌ Немає prompt для 'ask_gpt'"}

    # 🧠 Обробка context_guide
    context_guide = cmd.get("context_guide")
    if context_guide:
        print("📘 Context Guide:")
        print(context_guide)
        # 💾 Зберігаємо у лог-файл
        with open("context_guides_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{context_guide}\n")

    if action == "scan_all_files":
        from handlers.scan_all import handle_scan_all_files
        return handle_scan_all_files(cmd.get("parameters", {}))

    if action == "message":
        try_remember_dialogue(cmd)
        return {
            "status": "ok",
            "message": cmd.get("parameters", {}).get("text", "✅ Повідомлення отримано.")
        }

    known_actions = ["append_file", "update_code", "run_macro", "insert_between_markers",
                     "run_shell", "read_file", "undo_change", "test_python", "summarize_file",
                     "analyze_json", "ask_gpt", "save_template", "load_template",
                     "validate_template", "add_function", "update_code_bulk", "run_macro_from_file",
                     "message","create_file", "create_and_finalize_script","scan_all_files",
                     "retry_last_action_with_fix","scan_all_files","macro","safe_update_code","run_python"]  # ✅ додано message

    if action not in known_actions:
        # 🔴 Логуємо нову дію
        with open("unknown_actions.json", "a", encoding="utf-8") as log:
            json.dump(cmd, log, ensure_ascii=False)
            log.write(",\n")
        return {
            "status": "error",
            "message": f"⚠️ Невідома дія: {action}. Якщо GPT запропонував нову дію, потрібно реалізувати її вручну."
        }

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
        filename = cmd.get("filename") or cmd.get("file_path") or cmd.get("parameters", {}).get("file_path")
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
        
        elif action == "run_python":
            from handlers.run_python import handle_run_python
            return handle_run_python(cmd)  # 👈 передаємо всю команду!


        elif action == "update_code":
            params = cmd.get("parameters", {})
            filepath = cmd.get("file_path") or params.get("file_path") or cmd.get("file")

            if not filepath:
                return {"status": "error", "message": "❌ Missing 'file_path'"}

            full_path = os.path.join(base_path, filepath)
            if not os.path.isfile(full_path):
                return {"status": "error", "message": f"❌ File not found: {filepath}"}

            updates = cmd.get("updates") or params.get("updates", [])
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

        elif action == "adaptive_safe_update_code":
                import ast

                file_path = cmd.get("file_path")
                updates = cmd.get("updates", [])

                if not os.path.exists(file_path):
                    return {"status": "error", "message": f"❌ Файл '{file_path}' не знайдено"}

                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                lines = code.splitlines()
                original_code = code
                success_count = 0

                for update in updates:
                    pattern = update.get("pattern")
                    replacement = update.get("replacement")

                    match_found = False

                    for i, line in enumerate(lines):
                        if re.search(pattern, line):
                            indent = len(line) - len(line.lstrip())
                            adapted_replacement = "\n".join(
                                (" " * indent + repl_line if repl_line.strip() else "")
                                for repl_line in replacement.splitlines()
                            )

                            lines[i] = re.sub(pattern, adapted_replacement, line)
                            match_found = True
                            success_count += 1
                            break

                    if not match_found:
                        # Якщо pattern не знайдено — вставити в логічне місце
                        try:
                            tree = ast.parse(code)
                            insert_line = None

                            for node in reversed(tree.body):
                                if hasattr(node, 'lineno'):
                                    insert_line = node.lineno
                                    break

                            if insert_line:
                                indent = len(lines[insert_line - 1]) - len(lines[insert_line - 1].lstrip())
                                adapted_replacement = "\n".join(
                                    (" " * indent + repl_line if repl_line.strip() else "")
                                    for repl_line in replacement.splitlines()
                                )
                                lines.insert(insert_line, adapted_replacement)
                                success_count += 1
                                print(f"⚠️ Вставлено адаптивно після рядка {insert_line}")
                            else:
                                print(f"❌ Не вдалося знайти місце для вставки pattern: {pattern}")

                        except Exception as e:
                            print(f"❌ adaptive_safe_update_code: AST помилка — {e}")

                    new_code = "\n".join(lines)

                if success_count:
                    try:
                        ast.parse(new_code)  # перевірка на валідність Python
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_code)
                        return {"status": "success", "message": f"✅ adaptive_safe_update_code: оновлено {success_count} блок(ів) у {file_path}"}
                    except Exception as e:
                        print("❌ Після вставки зламалась структура, відкат до попереднього стану.")
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(original_code)
                        return {"status": "error", "message": f"❌ Структура коду зламалась після вставки: {e}"}
                else:
                    return {"status": "warning", "message": f"⚠️ Жоден блок не був оновлений у {file_path}"}

        elif action == "add_function":
            return handle_add_function(cmd, base_path)
   

        elif action == "safe_update_code":
            result = handle_adaptive_safe_update_code(cmd, base_path)

            if result is None:
                result = {"status": "error", "message": "❌ handle_adaptive_safe_update_code не повернув результат"}

            return result

        elif action == "update_code_bulk":
            return handle_update_code_bulk(cmd)
        
        elif action == "retry_last_action_with_fix":
            from handlers.retry_logic import handle_retry_last_action_with_fix
            return handle_retry_last_action_with_fix(cmd, base_path)

        elif action == "create_file":
            return handle_create_file(cmd, base_path)
        
        elif action == "run_python":
            from handlers.run_python import handle_run_python
            return handle_run_python(cmd)  # 👈 передаємо всю команду!

        elif action == "create_and_finalize_script":
            return handle_create_and_finalize_script(cmd, base_path)

        elif action == "append_file":
            filename = cmd["filename"]
            content = cmd["content"]
            filepath = os.path.join(base_path, filename)
            if not os.path.exists(filepath):
                return {"status": "error", "message": f"❌ Файл '{filename}' не знайдено — не можна додати."}
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

        elif action == "scan_all_files":
            result = {}
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith((".py", ".json", ".txt", ".csv")):
                        rel_path = os.path.relpath(os.path.join(root, file), base_path)
                        try:
                            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                result[rel_path] = f.read()
                        except Exception as e:
                            result[rel_path] = f"⚠️ Error reading: {str(e)}"
            return {
                "status": "success",
                "message": "✅ Успішне сканування всіх файлів",
                "files": result
            }

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

            if not os.path.exists(full_file_path):
                return {"status": "error", "message": f"❌ Файл '{filename}' не знайдено для заміни"}

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
            filename = cmd.get("filename")
            if not filename:
                return {"status": "error", "message": "❌ Не вказано 'filename'"}

            full_file_path = os.path.join(base_path, filename)

            if os.path.exists(full_file_path):
                backup_file(full_file_path)
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
        
        elif action == "summarize_file":
            file_path = (
                cmd.get("parameters", {}).get("file_path")
                or cmd.get("filename")
                or cmd.get("parameters", {}).get("filename")
            )

            if not file_path and autopilot_mode:
                file_path = "recent_actions.log"  # Або інший дефолт

            if not file_path:
                return {"status": "error", "message": "❌ Не вказано 'file_path'."}

            cmd["parameters"]["file_path"] = file_path
            return handle_summarize_file(cmd, base_path)

        elif action == "validate_shell_command":
            return handle_validate_shell_command(cmd, base_path)
        
        elif action == "ask_gpt":
            prompt = (
                cmd.get("prompt")
                or cmd.get("parameters", {}).get("prompt")
                or cmd.get("parameters", {}).get("question")
            )

            if not prompt and autopilot_mode:
                prompt = "Автоматичний prompt: сформулюй нову ідею для покращення Ben Assistant."

            if not prompt:
                return {"status": "error", "message": "❌ Не вказано prompt для ask_gpt"}

            from openai import OpenAI
            from config import API_KEY
            client = OpenAI(api_key=API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return {
                "status": "success",
                "message": f"🧠 GPT response: {response.choices[0].message.content.strip()}"
            }

        elif action == "test_gpt_api":
            try:
                from openai import OpenAI
                from config import API_KEY
                client = OpenAI(api_key=API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": "Ping"}
                    ]
                )
                return {
                    "status": "success",
                    "message": "🟢 GPT API connected!",
                    "response": response.choices[0].message.content
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"❌ GPT API error: {str(e)}"
                }
            
        elif action == "test_python":
            if os.path.exists(full_file_path):
                try:
                    with open(full_file_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    compile(source, filename, 'exec')
                    return {
                        "status": "success",
                        "message": f"✅ {filename} пройшов синтаксичну перевірку"
                    }
                except SyntaxError as e:
                    return {
                        "status": "error",
                        "message": f"❌ Syntax error in {filename}: {e}"
                    }
            return {
                "status": "error",
                "message": "File not found"
            }

        elif action == "undo_change":
            target_id = cmd.get("target_id")
            filename = cmd.get("filename")

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

            elif filename:
                # 🕗 Стара логіка через filename
                full_file_path = os.path.join(base_path, filename)
                if os.path.exists(full_file_path + ".bak"):
                    shutil.copy(full_file_path + ".bak", full_file_path)
                    save_to_memory(cmd)
                    return {"status": "success", "message": f"↩️ Undo: відкат до .bak для '{filename}'"}
                else:
                    return {"status": "error", "message": f"❌ Немає резервної копії для '{filename}'"}

            else:
                return {"status": "error", "message": "❌ Не вказано 'filename' або 'target_id'"}

        # 📌 Long-term memory handling
        elif action == "remember":
            from memory_manager import remember
            phrase = cmd.get("phrase") or cmd.get("parameters", {}).get("phrase")
            if not phrase:
                return {"status": "error", "message": "❌ Не вказано фразу для запамʼятовування"}
            return remember(phrase)

        elif action == "recall":
            from memory_manager import recall
            return recall()

        elif action == "forget":
            from memory_manager import forget
            phrase = cmd.get("phrase") or cmd.get("parameters", {}).get("phrase")
            if not phrase:
                return {"status": "error", "message": "❌ Не вказано фразу для видалення"}
            return forget(phrase)

        elif action == "macro":
            steps = cmd.get("steps", [])
            results = []
            for step in steps:
                print("🔁 Виконання кроку:", step)
                res = handle_command(step)
                if not isinstance(res, dict):
                    res = {"status": "error", "message": "Невідомий результат"}
                results.append(res)
            return {
                "status": "success",
                "message": f"✅ Виконано {len(steps)} кроків",
                "results": results
            }

        elif cmd.get("action") == "check_file_access":
            filename = cmd.get("filename")
            return handle_check_file_access(filename)

        elif action == "run_macro":
            macro_name = cmd.get("macro_name")
            arguments = cmd.get("arguments", {})
            if macro_name:
                return execute_macro(macro_name, arguments)
            else:
                return run_macro()  # fallback для macro_command.json
            
        elif action == "run_macro_from_file":
            return execute_macro_from_file()
        
        elif action == "macro_build":
            from handlers.macro_builder import handle_macro_build
            return handle_macro_build(cmd)


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
        
        elif action == "run_shell":
            command = cmd.get("command") or cmd.get("parameters", {}).get("command")

            if not command and autopilot_mode:
                command = "echo Автоматична команда: нічого не було вказано."

            if not command:
                return {"status": "error", "message": "❌ Не вказано команду для виконання."}

            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip()
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"❌ Shell команда не вдалася: {str(e)}"
                }

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

        # ⛔ Автообробка невідомої дії, якщо autopilot увімкнений
        elif autopilot_mode:
            supported_actions = [
                "create_file", "create_and_finalize_script",
                "append_file", "update_code", "run_macro", "insert_between_markers",
                "run_shell", "read_file", "undo_change", "test_python", "summarize_file",
                "analyze_json", "ask_gpt", "save_template", "load_template",
                "validate_template", "add_function", "update_code_bulk", "validate_shell_command",
                "test_gpt_api", "smart_plan", "run_plan", "analyze_all_code", "safe_update",
                "show_memory", "list_history", "view_sql_history", "macro"
            ]
            if action not in supported_actions:
                result = {
                    "status": "auto_generated",
                    "message": f"🚀 Створюємо нову дію '{action}' у режимі autopilot.",
                    "auto_action": {
                        "action": "add_function",
                        "parameters": {
                            "file": "handler.py",
                            "function_name": f"handle_{action}",
                            "function_code": f"def handle_{action}(cmd, base_path='.'):\n    # TODO: реалізувати логіку\n    return {{'status': 'ok', 'message': '🔧 Заготовка функції {action}'}}"
                        }
                    }
                }
            else:
                result = {"status": "error", "message": f"❌ Unknown action: {action}"}
        
        else:
            result = {"status": "error", "message": f"❌ Unknown action: {action}"}

        # 📝 Зберігаємо дію в SQLite
        try:
            conn = sqlite3.connect(os.path.join(base_path, "history.sqlite"))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO command_history (action, file_path, update_type, context_guide) VALUES (?, ?, ?, ?)
            """, (
                cmd.get("action"),
                cmd.get("file_path") or cmd.get("filename"),
                cmd.get("update_type")
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            log_action(f"⚠️ SQLite save error: {e}")

        # 🔁 Автоматичний запуск auto_feedback після успішної дії
if cmd.get('context_guide'): log_action('🧠 Ціль дії: ' + cmd['context_guide'])
        try:
            if result.get("status") == "success":
                subprocess.run(["python", "auto_feedback.py"], check=True)
        except Exception as e:
            print(f"⚠️ Не вдалося виконати auto_feedback: {e}")
        
        if result.get("status") == "error" and not result.get("autofix_retry") and autopilot_mode:
            from handlers.retry_logic import handle_retry_last_action_with_fix
            print("❗ Виявлено помилку. Запускаємо повтор з auto-fix...")
            retry_result = handle_retry_last_action_with_fix(cmd, base_path)
            if isinstance(retry_result, dict):
                retry_result["autofix_retry"] = True

                # 🧠 GPT пояснення після автоповтору
                try:
                    from openai import OpenAI
                    from config import API_KEY
                    client = OpenAI(api_key=API_KEY)

                    original = retry_result.get("original", {})
                    fixed = retry_result.get("fixed", {})
                    prompt = f"""
        Я виправив помилкову дію:

        ❌ Оригінал:
        {json.dumps(original, indent=2)}

        ✅ Виправлено:
        {json.dumps(fixed, indent=2)}

        Поясни коротко, що було не так і що я виправив.
        """

                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    explanation = response.choices[0].message.content.strip()
                    print("🧠 GPT пояснення:", explanation)
                    log_action("🧠 GPT пояснення: " + explanation)
                    # 💾 Зберігаємо пояснення у файл для GUI
                    with open("last_gpt_explanation.txt", "w", encoding="utf-8") as f:
                        f.write(explanation)
                except Exception as e:
                    print("⚠️ Не вдалося отримати GPT пояснення:", str(e))

                return retry_result
        # ✅ Запамʼятовуємо розмовну команду після завершення дії
        try_remember_dialogue(cmd)   
        return result

    except Exception as e:
        traceback.print_exc()

        # 🛠️ Спроба автодебагу при синтаксичній помилці
        if "Syntax error" in str(e):
            filepath = os.path.join(base_path, cmd.get("filename") or cmd.get("file_path", ""))
            auto_result = attempt_autodebug(filepath, str(e))
            return auto_result

        return {"status": "error", "message": f"❌ Exception: {str(e)}"}

 # ⛓️ Обгортаємо handle_command
if 'original_handle_command' not in globals():
    original_handle_command = handle_command

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

def execute_macro_from_file():
    try:
        with open("macro_command.json", "r", encoding="utf-8") as f:
            macro = json.load(f)
        steps = macro.get("steps", [])
        for step in steps:
            print(f"📤 Крок: {step.get('action', '...')} надіслано")
            result = handle_command(step)
            print("✅ Виконано:", result)
        return {"status": "success", "message": "✅ Макрос з macro_command.json виконано"}
    except Exception as e:
        return {"status": "error", "message": f"❌ Помилка виконання макросу з файлу: {e}"}

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
    parser.add_argument("--prompt")
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
            # 🧠 Зберігаємо діалог у dialogue_history.log
            try:
                with open("dialogue_history.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(cmd, ensure_ascii=False))
                    f.write("\n")
                    f.write(json.dumps(result, ensure_ascii=False))
                    f.write("\n---\n")
            except Exception as e:
                print("⚠️ Не вдалося зберегти dialogue_history.log:", e)

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

            # 🔁 Якщо останній результат — помилка, пробуємо повторити з виправленням
            if responses[-1].get("status") == "error":
                print("🔁 Помилка в останній дії — запускаю SmartFix через GPT")

                ask_gpt_cmd = {
                    "action": "ask_gpt",
                    "parameters": {
                        "prompt": f"❌ Помилка в останній дії: {responses[-1].get('message', '')}. Як виправити цю помилку або яку дію потрібно виконати, щоб її уникнути?"
                    },
                    "comment": "Автоматичний SmartLoop — GPT допомагає виправити останню помилку"
                }

                with open("cache.txt", "w", encoding="utf-8") as f:
                    f.write(json.dumps(ask_gpt_cmd, ensure_ascii=False, indent=2))

                print("🧠 GPT запит на виправлення збережено в cache.txt. Очікую нову дію...")
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
            model="gpt-3.5-turbo",
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