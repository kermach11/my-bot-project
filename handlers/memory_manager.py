# handlers/memory_manager.py
import json
import os

MEMORY_PATH = "long_term_memory.json"


def load_memory():
    if not os.path.exists(MEMORY_PATH):
        return {
            "user_preferences": [],
            "forbidden_behaviors": [],
            "key_commands": [],
            "reminders": []
        }
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(memory):
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def remember_phrase(phrase):
    memory = load_memory()
    memory["reminders"].append(phrase)
    save_memory(memory)
    return f"🧠 Запамʼятав: {phrase}"


def recall_memory():
    memory = load_memory()
    return memory.get("reminders", [])


def forget_phrase(phrase):
    memory = load_memory()
    if phrase in memory["reminders"]:
        memory["reminders"].remove(phrase)
    save_memory(memory)
    return f"🧠 Забув: {phrase}"


def is_forbidden_action(action):
    memory = load_memory()
    return action in memory.get("forbidden_behaviors", [])
