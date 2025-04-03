import os

def handle_scan_all_files(params=None):
    """
    Сканує всі .py файли в поточній директорії та підпапках, повертає словник {шлях: вміст}
    """
    result = {}
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    result[path] = content
                except Exception as e:
                    result[path] = f"[ERROR reading file: {e}]"
    return {
        "status": "ok",
        "message": "📂 Успішно проскановано всі файли",
        "files": result
    }
