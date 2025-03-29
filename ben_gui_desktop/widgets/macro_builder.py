import tkinter as tk
from tkinter import ttk, messagebox
import json
import time

class MacroBuilder(ttk.Frame):
    def __init__(self, parent, response_area):
        super().__init__(parent)
        self.response_area = response_area
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

        self.fields_frame = ttk.Frame(self)
        self.fields_frame.pack(fill=tk.X, padx=5, pady=5)
        self.field_vars = {
            "action": tk.StringVar(),
            "filename": tk.StringVar(),
            "pattern": tk.StringVar(),
            "replacement": tk.StringVar(),
            "content": tk.StringVar(),
            "delay": tk.StringVar()
        }

        for label, var in self.field_vars.items():
            row = ttk.Frame(self.fields_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label.capitalize() + ":").pack(side=tk.LEFT, padx=(0, 5))
            entry = ttk.Entry(row, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(self, text="➕ Add Full Step", command=self.add_full_step).pack(pady=5)
        ttk.Button(self, text="🧪 Preview & Validate", command=self.preview_macro).pack(pady=5)
        ttk.Button(self, text="💾 Save Macro", command=self.save_macro).pack(pady=5)

    def add_step(self):
        action = self.action_var.get().strip()
        if action:
            self.steps.append({"action": action})
            self.listbox.insert(tk.END, action)
            self.action_var.set("")

    def add_full_step(self):
        step = {}
        for key, var in self.field_vars.items():
            value = var.get().strip()
            if value:
                if key == "delay":
                    try:
                        step[key] = float(value)
                    except ValueError:
                        self.response_area.insert(tk.END, f"⚠️ Невірне значення delay: {value}\n")
                        return
                else:
                    step[key] = value
        if step:
            self.steps.append(step)
            self.listbox.insert(tk.END, step.get("action", "[No action]"))
            for var in self.field_vars.values():
                var.set("")

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
        try:
            with open("macro_command.json", "w", encoding="utf-8") as f:
                json.dump(macro, f, indent=2)
            messagebox.showinfo("Saved", "✅ Macro saved to macro_command.json")
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to save macro: {e}")

    def preview_macro(self):
        try:
            msg = f"🧪 Превʼю макросу: {len(self.steps)} кроків\n"
            for i, step in enumerate(self.steps, 1):
                msg += f"  {i}. {step.get('action', '...')}"
                if "delay" in step:
                    msg += f" (⏳ delay: {step['delay']}s)"
                msg += "\n"
            self.response_area.insert(tk.END, msg)
        except Exception as e:
            self.response_area.insert(tk.END, f"❌ Помилка валідації макросу: {e}\n")
        self.response_area.see(tk.END)

    def run_macro(self):
        try:
            with open("macro_command.json", "r", encoding="utf-8") as f:
                macro = json.load(f)

            steps = macro.get("steps", [])
            self.response_area.insert(tk.END, f"✅ Запущено макрос '{macro.get('name', 'Без назви')}' з {len(steps)} кроків\n")
            self.response_area.see(tk.END)
            for step in steps:
                delay = step.get("delay", 0)
                if delay > 0:
                    self.response_area.insert(tk.END, f"⏳ Затримка {delay} сек перед дією: {step.get('action', '...')}\n")
                    self.response_area.see(tk.END)
                    time.sleep(delay)

                with open("request.json", "w", encoding="utf-8") as f:
                    json.dump([step], f, indent=2)
                self.response_area.insert(tk.END, f"📤 Крок: {step.get('action', '...')} надіслано\n")
                self.response_area.see(tk.END)
                time.sleep(1.5)
        except Exception as e:
            messagebox.showerror("Помилка", f"❌ Не вдалося виконати макрос: {e}")
