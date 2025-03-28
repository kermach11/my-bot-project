import tkinter as tk
from tkinter import ttk

class UserProfilePanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        style = ttk.Style()
        style.configure("TLabel", font=("Helvetica", 11))
        style.configure("TCombobox", padding=6)
        style.configure("TCheckbutton", padding=6)

        ttk.Label(self, text="👤 Профіль користувача", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))

        # Тема інтерфейсу
        ttk.Label(self, text="🎨 Тема інтерфейсу:").pack(anchor="w")
        self.theme_var = tk.StringVar(value="light")
        ttk.Combobox(self, textvariable=self.theme_var, values=["light", "dark", "system"]).pack(fill=tk.X, pady=5)
# Застосування теми при зміні
        def apply_theme(event=None):
            selected = self.theme_var.get()
            if selected == "dark":
                parent.tk_setPalette(background="#1e1e1e", foreground="#ffffff")
            elif selected == "light":
                parent.tk_setPalette(background="#ffffff", foreground="#000000")
            else:
                parent.tk_setPalette(background=None, foreground=None)

        self.theme_var.trace_add("write", lambda *args: apply_theme())
        apply_theme()

        # Роль користувача
        ttk.Label(self, text="🔐 Роль:").pack(anchor="w")
        self.role_var = tk.StringVar(value="developer")
        ttk.Combobox(self, textvariable=self.role_var, values=["developer", "admin", "viewer"]).pack(fill=tk.X, pady=5)

        # Фільтрація журналу
        ttk.Label(self, text="🔍 Фільтр подій:").pack(anchor="w")
        self.filter_var = tk.StringVar(value="all")
        ttk.Combobox(self, textvariable=self.filter_var, values=["all", "commands", "errors", "system"]).pack(fill=tk.X, pady=5)

        # Прогалини для естетики
        ttk.Label(self, text="").pack(pady=10)

    def get_profile_settings(self):
        return {
            "theme": self.theme_var.get(),
            "role": self.role_var.get(),
            "filter": self.filter_var.get()
        }