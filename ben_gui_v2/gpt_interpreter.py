import os
import json

def interpret_user_prompt(prompt, context_code=None, return_data=False):
    from openai import OpenAI
    from config import API_KEY
    import json

    client = OpenAI(api_key=API_KEY)

    system_msg = {
        "role": "system",
        "content": (
            "Ти працюєш в системі Ben Assistant. Твоя задача — на основі промпту користувача "
            "та контексту коду (якщо є) згенерувати дію у форматі JSON, яку агент зможе виконати. "
            "Поверни лише один JSON-обʼєкт. "
            "Дозволені дії: append_file, update_code, run_macro, insert_between_markers, run_shell тощо. "
            "Не використовуй вигадані дії на кшталт 'create_function' — використовуй append_file з параметрами filename і content."
        )
    }

    # Додати контекст до запиту, якщо він є
    if context_code:
        prompt = f"📄 Контекст коду:\n{context_code}\n\n🧠 Завдання: {prompt}"

    user_msg = {"role": "user", "content": prompt}

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[system_msg, user_msg],
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    print("[GPT RAW OUTPUT]\n", raw)

    try:
        data = json.loads(raw)
        with open("cache.txt", "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
        print("✅ Збережено в cache.txt")
        if return_data:
            return data
    except Exception as e:
        print(f"❌ Не вдалося розпізнати JSON: {e}")
        if return_data:
            return None
