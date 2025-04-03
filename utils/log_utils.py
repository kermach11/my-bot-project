import os
from datetime import datetime, timezone
from config import history_file

def log_action(message: str):
    """
    Логує повідомлення у файл історії з таймштампом у UTC.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    try:
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"⚠️ Log write error: {e}")
