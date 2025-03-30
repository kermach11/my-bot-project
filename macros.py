import json
from gpt_agent_cache import handle_command

def run_macro(cmd):
    name = cmd.get("name")
    params = cmd.get("parameters", {})

    if name == "undo_last_change":
        target_id = params.get("target_id")
        if not target_id:
            return {"status": "error", "message": "❌ Не вказано target_id для undo"}

        undo_cmd = {
            "action": "undo_change",
            "target_id": target_id
        }
        return handle_command(undo_cmd)

    elif name == "scan_all_on_start":
        steps = [
            {"action": "scan_all_files"},
            {"action": "analyze_all_code"}
        ]
        for step in steps:
            result = handle_command(step)
            if result.get("status") != "success":
                return {"status": "error", "message": f"❌ Помилка при {step['action']}: {result.get('message')}"}
        return {"status": "success", "message": "✅ Сканування та аналіз завершено"}

    return {"status": "error", "message": f"❌ Невідома макрокоманда: {name}"}
