import sqlite3
import os

def create_history_table():
    base_path = os.path.dirname(__file__)
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
