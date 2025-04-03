import os
import re

def auto_guess_missing_parameters(cmd):
    parameters = cmd.get("parameters", {})

    for key in ["file_path", "name", "code"]:
        val = cmd.get(key) or parameters.get(key)
        if isinstance(val, str) and any(bad in val.lower() for bad in ["вкажіть", "path/to", "ім'я", "назву"]):
            if key == "file_path":
                for fname in os.listdir():
                    if fname.endswith(".py") and fname not in ["gpt_agent_cache.py", "auto_feedback.py"]:
                        parameters["file_path"] = fname
                        break
                else:
                    parameters["file_path"] = "example.py"

            elif key == "name":
                code_text = parameters.get("code", "")
                match = re.search(r"def\s+(\w+)", code_text)
                if match:
                    parameters["name"] = match.group(1)

            elif key == "code":
                continue

    # ⛑️ Створити файл, якщо він не існує
    if "file_path" in parameters:
        fp = parameters["file_path"]
        if not os.path.exists(fp):
            dir_path = os.path.dirname(fp)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                f.write("# 🆕 Автоматично створений файл\n")


    # 🔁 fallback для name, якщо є code, але немає name
    if "name" not in parameters or not parameters["name"]:
        code_text = parameters.get("code", "")
        match = re.search(r"def\s+(\w+)", code_text)
        if match:
            parameters["name"] = match.group(1)

    cmd["parameters"] = parameters
    return cmd