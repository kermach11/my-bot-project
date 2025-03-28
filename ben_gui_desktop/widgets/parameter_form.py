import tkinter as tk
from tkinter import ttk

class ParameterForm(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.entries = {}
        self.fields = [
            "filename", "content", "pattern", "replacement",
            "update_type", "insert_at_line", "rollback_on_fail"
        ]

        for field in self.fields:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=field + ":", width=18).pack(side=tk.LEFT)
            entry = ttk.Entry(row)
            entry.pack(fill=tk.X, expand=True)
            self.entries[field] = entry

    def get_command_fields(self):
        result = {}
        for field, entry in self.entries.items():
            value = entry.get().strip()
            if value:
                # Автоматично перетворюємо rollback_on_fail в bool
                if field == "rollback_on_fail":
                    result[field] = value.lower() in ["true", "1", "yes"]
                elif field == "insert_at_line":
                    try:
                        result[field] = int(value)
                    except ValueError:
                        pass  # Ігноруємо некоректне число
                else:
                    result[field] = value
        return result

    def clear(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)