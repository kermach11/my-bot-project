import os
import json

def handle_retry_last_action_with_fix(cmd, base_path="."):
    from .auto_fix import auto_fix_parameters
    from gpt_agent_cache import handle_command

    memory_file = os.path.join(base_path, ".ben_memory.json")
    if not os.path.exists(memory_file):
        return {"status": "error", "message": "❌ Файл памʼяті не знайдено"}

    with open(memory_file, "r", encoding="utf-8") as f:
        memory = json.load(f)

    if not memory:
        return {"status": "error", "message": "❌ Немає останньої дії для повтору"}

    last_cmd = memory[-1]
    fixed_cmd = auto_fix_parameters(last_cmd)

    result = handle_command(fixed_cmd)
    return {
        "status": "retry",
        "original": last_cmd,
        "fixed": fixed_cmd,
        "result": result
    }
