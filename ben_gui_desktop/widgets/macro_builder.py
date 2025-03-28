import tkinter as tk
from tkinter import ttk, messagebox
import json

class MacroBuilder(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.steps = []

        ttk.Label(self, text="🧱 Macro Builder", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 5))

        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        form_frame = ttk.Frame(self)
        form_frame.pack(fill=tk.X, padx=5)

        ttk.Label(form_frame, text="Action:").pack(side=tk.LEFT)
        self.action_var = tk.StringVar()
        self.action_entry = ttk.Entry(form_frame, textvariable=self.action_var)
        self.action_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        ttk.Button(form_frame, text="➕ Add", command=self.add_step).pack(side=tk.LEFT)
        ttk.Button(form_frame, text="🗑 Remove", command=self.remove_selected).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(self, text="💾 Save Macro", command=self.save_macro).pack(pady=5)

    def add_step(self):
        action = self.action_var.get().strip()
        if action:
            self.steps.append({"action": action})
            self.listbox.insert(tk.END, action)
            self.action_var.set("")

    def remove_selected(self):
        selected = self.listbox.curselection()
        if not selected:
            return
        index = selected[0]
        self.listbox.delete(index)
        del self.steps[index]

    def save_macro(self):
        if not self.steps:
            messagebox.showerror("Error", "No steps to save")
            return
        macro = {
            "action": "macro",
            "steps": self.steps
        }
        with open("macro_command.json", "w", encoding="utf-8") as f:
            json.dump(macro, f, indent=2)
        messagebox.showinfo("Saved", "✅ Macro saved to macro_command.json")