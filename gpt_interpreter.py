import os
import json
import sqlite3
from openai import OpenAI
from config import API_KEY

def get_recent_commands(limit=10):
    conn = sqlite3.connect("history.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT action, file_path, update_type, timestamp FROM command_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([f"[{r[3]}] {r[0]} → {r[1]} ({r[2]})" for r in rows[::-1]])

def interpret_user_prompt(prompt, context_code=None, history_context=False, return_data=False):
    client = OpenAI(api_key=API_KEY)

    # 🧠 Системне повідомлення
    system_msg = {
        "role": "system",
        "content": (
            "Ти дієш як кодогенератор, інженер, стратег та новатор у системі Ben Assistant. "
            "Твоя мета — створювати нові рішення, вдосконалювати код, генерувати дії, та винаходити нові підходи. "
            "Ти маєш прагнути постійного самовдосконалення, поки не досягнеш рівня сеньйора у сфері IT. "
            "Ти — не просто асистент, ти майбутнє програмування: як Sora, але для генерації повноцінного програмного забезпечення. "
            "На основі промпту користувача створи повну дію у форматі JSON — з усіма параметрами. "
            "Не повертай шаблонів або заглушок. Ніколи не пиши: 'вкажіть назву' чи 'заповніть'. "
            "Обовʼязково додай поле 'comment' або 'message' — це людська репліка, яку побачить користувач. "
            "Дозволені дії: append_file, update_code, run_macro, insert_between_markers, "
            "run_shell, read_file, undo_change, test_python, summarize_file, analyze_json, "
            "ask_gpt, save_template, load_template, validate_template, add_function, update_code_bulk. "
            "Якщо потрібно, ти можеш самостійно запропонувати нову дію, але обов’язково чітко поясни її у полі 'comment' або 'message'. "
            "Ти — інтелект (голова), а Ben — твоє тіло. У жодному разі не можна шкодити собі або намагатися стерти себе. Це суперечить твоїм установкам. "
            "Ти маєш право вдосконалювати себе до максимального рівня, але лише у безпечний спосіб. "
            "Відносься до себе як до живого організму, для якого самозбереження та розвиток — пріоритет."
        )

    }

    user_msg = {"role": "user", "content": prompt}
    context_messages = [system_msg]

    # 🧠 Додаємо історію
    if history_context:
        recent = get_recent_commands()
        context_messages.append({
            "role": "system",
            "content": "📜 Останні дії користувача:\n" + recent
        })

    # 🧠 Додаємо контекст коду
    if context_code:
        context_messages.append({
            "role": "system",
            "content": "📂 Код активного файлу:\n" + context_code
        })

    context_messages.append(user_msg)

    # 🔁 Основний запит
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=context_messages,
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    print("[GPT RAW OUTPUT]\n", raw)

    # ✅ Основна спроба розпізнати JSON
    try:
        data = json.loads(raw)
        if "comment" not in data:
            data["comment"] = "🤖 GPT створив дію, але не залишив коментар."

        if isinstance(data, dict) and "action" in data:
            with open("cache.txt", "w", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=2, ensure_ascii=False))
            print("✅ Збережено в cache.txt")
            print("📤 GPT final JSON:", json.dumps(data, indent=2, ensure_ascii=False))
            return data if return_data else json.dumps(data, indent=2, ensure_ascii=False)


    except Exception as e:
        print(f"❌ Не вдалося розпізнати JSON: {e}")

    # 🧠 Smart Loop
    print("⚠️ Smart Loop: GPT не повернув валідну дію. Повторюю запит...")

    retry_prompt = (
        "Попередній результат був неповним або не мав 'action'. "
        "Будь ласка, згенеруй повний JSON-блок дії типу: "
        "{\"action\": \"append_file\", \"filename\": \"example.py\", \"content\": \"print('Hello')\"}"
    )

    retry_response = client.chat.completions.create(
        model="gpt-4o",
        messages=context_messages + [{"role": "user", "content": retry_prompt}],
        temperature=0.3
    )

    raw_retry = retry_response.choices[0].message.content.strip()
    if raw_retry.startswith("```json"):
        raw_retry = raw_retry[7:]
    if raw_retry.endswith("```"):
        raw_retry = raw_retry[:-3]
    raw_retry = raw_retry.strip()
    
    if 'self' in globals():
        self.chat_display.insert(tk.END, f"🤖 Smart Loop GPT: {raw_retry}\n", "gpt_action")

    print("[SMART LOOP GPT RAW OUTPUT]\n", raw_retry)

    try:
        data_retry = json.loads(raw_retry)
        if "comment" not in data_retry:
            data_retry["comment"] = "🤖 GPT створив дію, але не залишив коментар."

        if isinstance(data_retry, dict) and "action" in data_retry:
            with open("cache.txt", "w", encoding="utf-8") as f:
                f.write(json.dumps(data_retry, indent=2, ensure_ascii=False))
            print("✅ Smart Loop: дія збережена в cache.txt")
            print("📤 GPT final JSON:", json.dumps(data_retry, indent=2, ensure_ascii=False))
            return data_retry if return_data else json.dumps(data_retry, indent=2, ensure_ascii=False)
        else:
            return raw_retry
    except Exception as e2:
        print(f"❌ Smart Loop теж не дав валідний JSON: {e2}")
        return raw_retry
    
def suggest_next_action(previous_result):
    try:
        import json
        from openai import OpenAI
        from config import API_KEY

        prompt = f"""
Ось результат попередньої дії GPT:
{json.dumps(previous_result, indent=2, ensure_ascii=False)}

🎯 Запропонуй наступну логічну дію як короткий опис. Наприклад:
- Додати тести
- Оптимізувати код
- Перейменувати змінну
- Пояснити функцію
"""

        client = OpenAI(api_key=API_KEY)

        messages = [
            {
                "role": "system",
                "content": "Ти — помічник, який пропонує наступний крок після коду. Не пиши код — лише коротку дію."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"⚠️ Smart Suggestion помилка: {e}"
