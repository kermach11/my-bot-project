import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import time
import os
from datetime import datetime
timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
# 💡 GPT: DO NOT DELETE — used in generate_macro_from_prompt()
import requests
from logic.gpt_macro_engine import GPTMacroEngine
from dotenv import load_dotenv
load_dotenv()

USE_OPENAI_API = True  # 🔁 Перемикач між OpenAI API та локальним GPT-сервером

class DragDropListbox(tk.Listbox):
    def __init__(self, master, **kw):
        kw['selectmode'] = tk.SINGLE
        super().__init__(master, kw)
        self.bind('<Button-1>', self.set_current)
        self.bind('<B1-Motion>', self.shift_selection)
        self.curIndex = None

    def set_current(self, event):
        self.curIndex = self.nearest(event.y)

    def shift_selection(self, event):
        i = self.nearest(event.y)
        if i < self.curIndex:
            x = self.get(i)
            self.delete(i)
            self.insert(i + 1, x)
            self.curIndex = i
        elif i > self.curIndex:
            x = self.get(i)
            self.delete(i)
            self.insert(i - 1, x)
            self.curIndex = i

class MacroBuilder(ttk.Frame):
    def __init__(self, parent, response_area):
        super().__init__(parent)
        self.response_area = response_area
        self.steps = []
        self.known_files = set()

        ttk.Label(self, text="🧱 Macro Builder", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 5))

        self.listbox = DragDropListbox(self)
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
            "delay": tk.StringVar(),
            "if": tk.StringVar()
        }

        for label, var in self.field_vars.items():
            row = ttk.Frame(self.fields_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label.capitalize() + ":").pack(side=tk.LEFT, padx=(0, 5))
            entry = ttk.Entry(row, textvariable=var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(self, text="➕ Add Full Step", command=self.add_full_step).pack(pady=5)
        ttk.Button(self, text="🧪 Preview & Validate", command=self.preview_macro).pack(pady=5)
        ttk.Button(self, text="📂 Save Macro", command=self.save_macro).pack(pady=5)
        ttk.Button(self, text="📂 Show Known Files", command=self.show_known_files).pack(pady=5)
        ttk.Button(self, text="🤖 GPT Macro Generator", command=self.generate_macro_from_prompt).pack(pady=5)

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

    def preview_macro(self):
        try:
            msg = f"🧪 Превʼю макросу: {len(self.steps)} кроків\n"
            for i, step in enumerate(self.steps, 1):
                msg += f"  {i}. {step.get('action', '...')}"
                if "delay" in step:
                    msg += f" (⏳ delay: {step['delay']}s)"
                if "if" in step:
                    msg += f" [if: {step['if']}]"
                msg += "\n"
            self.response_area.insert(tk.END, msg)
        except Exception as e:
            self.response_area.insert(tk.END, f"❌ Помилка валідації макросу: {e}\n")
        self.response_area.see(tk.END)

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

    def show_known_files(self):
        try:
            file_list = sorted(self.known_files)
            msg = "📂 Відомі файли:\n" + "\n".join(file_list)
            self.response_area.insert(tk.END, msg + "\n")
            self.response_area.see(tk.END)
        except Exception as e:
            self.response_area.insert(tk.END, f"❌ Помилка перегляду файлів: {e}\n")

    def save_known_files(self):
        try:
            with open(".ben_memory.json", "r", encoding="utf-8") as f:
                memory = json.load(f)
        except:
            memory = {}
        memory["known_files"] = sorted(self.known_files)
        with open(".ben_memory.json", "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2)

    def log_debug(self, message):
        with open("debug.log", "a", encoding="utf-8") as log:
            import datetime
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{timestamp}] {message}\n")

    
    def generate_macro_from_prompt(self):
        prompt = simpledialog.askstring("GPT Macro", "Введіть запит для GPT:")
        if not prompt:
            return
        self.response_area.insert(tk.END, "⏳ GPT думає...\n")
        threading.Thread(target=self._run_gpt_macro, args=(prompt,), daemon=True).start()

    def _run_gpt_macro(self, prompt):
        try:
            engine = GPTMacroEngine()
            steps = engine.generate_macro(prompt)
            self.steps.extend(steps)
            self.response_area.insert(tk.END, f"🤖 Додано {len(steps)} кроків від GPT\n")
            self.preview_macro()
        except Exception as e:
            self.response_area.insert(tk.END, f"❌ GPT генерація помилка: {e}\n")
        self.response_area.see(tk.END)

    def run_macro(self):
        try:
            with open("macro_command.json", "r", encoding="utf-8") as f:
                macro = json.load(f)
                macro_name = macro.get("name", "Без назви")
                steps = macro.get("steps", [])
                self.response_area.insert(tk.END, f"🧠 Запуск макросу '{macro_name}' — {len(steps)} кроків\n")
                self.response_area.see(tk.END)
                self.log_debug(f"▶️ Старт макросу '{macro_name}' з {len(steps)} кроків")

            for step in steps:
                try:
                    condition = step.get("if")
                    if condition:
                        if not eval(condition, {}, {"previous_status": "success"}):
                            msg = f"⏭ Пропущено через if: {condition}"
                            self.response_area.insert(tk.END, msg + "\n")
                            self.response_area.see(tk.END)
                            self.log_debug(msg)
                            continue

                    delay = step.get("delay", 0)
                    if delay > 0:
                        msg = f"⏳ Затримка {delay} сек перед дією: {step.get('action', '...')}"
                        self.response_area.insert(tk.END, msg + "\n")
                        self.response_area.see(tk.END)
                        self.log_debug(msg)
                        time.sleep(delay)

                    if step.get("action") == "rollback":
                        filename = step.get("filename")
                        if filename:
                            backup_path = os.path.join("backups", filename)
                            if not os.path.exists(backup_path):
                                msg = f"⚠️ Пропущено rollback — немає резервної копії для '{filename}'"
                                self.response_area.insert(tk.END, msg + "\n")
                                self.response_area.see(tk.END)
                                self.log_debug(msg)
                                continue

                    if not step.get("action"):
                        msg = "⚠️ Пропущено крок — відсутній 'action'"
                        self.response_area.insert(tk.END, msg + "\n")
                        self.log_debug(msg)
                        continue

                    if step.get("action") in ["update_code", "insert"]:
                        if not step.get("content"):
                            msg = "⚠️ Пропущено update — відсутній 'content'"
                            self.response_area.insert(tk.END, msg + "\n")
                            self.log_debug(msg)
                            continue

                    if step.get("filename"):
                        path = step.get("filename")
                        self.known_files.add(path)
                        if not os.path.exists(path):
                            msg = f"⚠️ Пропущено — файл '{path}' не існує"
                            self.response_area.insert(tk.END, msg + "\n")
                            self.log_debug(msg)
                            continue

                    with open("request.json", "w", encoding="utf-8") as f:
                        json.dump([step], f, indent=2)
                    msg = f"📤 Крок: {step.get('action', '...')} надіслано"
                    self.response_area.insert(tk.END, msg + "\n")
                    self.response_area.see(tk.END)
                    self.log_debug(msg)
                    time.sleep(1.5)
                except Exception as step_err:
                    self.log_debug(f"❌ Помилка кроку: {step_err}")
                    self.response_area.insert(tk.END, f"❌ Помилка кроку: {step_err}\n")

            self.save_known_files()

        except Exception as e:
            self.log_debug(f"❌ Помилка макросу: {e}")
            messagebox.showerror("Помилка", f"❌ Не вдалося виконати макрос: {e}")
