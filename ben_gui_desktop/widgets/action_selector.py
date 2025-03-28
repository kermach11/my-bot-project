import tkinter as tk
from tkinter import ttk

class ActionSelector(ttk.Frame):
    def __init__(self, parent, on_action_change):
        super().__init__(parent)
        self.on_action_change = on_action_change

        ttk.Label(self, text="Оберіть дію:").pack(anchor="w")

        self.action_var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.action_var)
        self.combo['values'] = [
            "create_file", "append_file", "update_code", "update_code_bulk",
            "replace_in_file", "delete_file", "rename_file", "macro",
            "list_history", "view_sql_history", "run_python"
        ]
        self.combo.bind("<<ComboboxSelected>>", self.action_selected)
        self.combo.pack(fill=tk.X)

    def action_selected(self, event):
        selected = self.action_var.get()
        self.on_action_change(selected)

    def get_selected_action(self):
        return self.action_var.get()