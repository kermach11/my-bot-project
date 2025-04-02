def auto_fix_parameters(cmd):
    """
    Автоматично виправляє некоректні параметри в команді (наприклад, 'unknown', None).
    Повертає оновлену команду.
    """
    if not isinstance(cmd, dict):
        return cmd

    fixed = dict(cmd)  # копія
    parameters = fixed.get("parameters", {})

    # Виправлення file_path
    file_path = parameters.get("file_path") or fixed.get("file_path") or fixed.get("filename")
    if not file_path or file_path == "unknown":
        parameters["file_path"] = "recent_actions.log"

    # Виправлення prompt
    prompt = parameters.get("prompt") or parameters.get("question") or fixed.get("prompt")
    if (not prompt or prompt == "unknown") and fixed.get("action") == "ask_gpt":
        parameters["prompt"] = "Автоматичний prompt: поясни логіку коду або виправ помилку."

    # Виправлення команд для run_shell
    if fixed.get("action") == "run_shell":
        command = fixed.get("command") or parameters.get("command")
        if not command or command == "unknown":
            parameters["command"] = "echo Автоматична команда: нічого не було вказано."

    # Виправлення вмісту create_file
    if fixed.get("action") == "create_file":
        content = parameters.get("content")
        if not content or content == "unknown":
            parameters["content"] = "# Автоматичний шаблон файлу\nprint('Hello, world!')"

    fixed["parameters"] = parameters
    return fixed
