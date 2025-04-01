import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
import threading
from tkinter import ttk, scrolledtext, Menu
import json
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
from gpt_interpreter import interpret_user_prompt  # 🔌 Підключення інтерпретатора
from gpt_agent_cache import handle_command, save_to_memory       # 🧠 Автовиконання команд
from openai import OpenAI                          # 🧠 GPT API для пояснення коду
from config import API_KEY
import time


class BenAssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ben Assistant v2")
        self.root.geometry("1200x700")

        self.current_chat_file = None
        self.chat_history = []
        self.last_action_id = None
        self.action_counter = 1  # 🔢 Для присвоєння унікального ID діям
        self.command_counter = 1  # 🔢 Для унікальних history_id
        self.current_file_content = ""  # 🧠 Зберігаємо код активного файлу

        self.setup_layout()

        # 🎨 Стилізація для тегу gpt_action
        self.chat_display.tag_configure("gpt_action", foreground="#0066cc", font=("Arial", 10, "bold", "italic"))
        self.chat_display.tag_configure("gpt_action", foreground="#0a84ff", font=("Arial", 10, "bold"))
        self.root.bind_all("<Control-c>", lambda e: self.root.focus_get().event_generate("<<Copy>>"))
        self.root.bind_all("<Control-v>", lambda e: self.root.focus_get().event_generate("<<Paste>>"))
        self.root.bind_all("<Control-x>", lambda e: self.root.focus_get().event_generate("<<Cut>>"))
        self.root.bind_all("<Control-a>", lambda e: self.root.focus_get().event_generate("<<SelectAll>>"))

        os.makedirs("chats", exist_ok=True)
        self.load_chats()

    def setup_layout(self):
        self.left_panel = tk.Frame(self.root, width=250, bg="#f0f0f0")
        self.left_panel.pack(side="left", fill="y")

        self.project_label = tk.Label(self.left_panel, text="🗂️ Стіл", bg="#f0f0f0", font=("Arial", 12, "bold"))
        self.project_label.pack(pady=(10,0))

        self.project_tree = ttk.Treeview(self.left_panel)
        self.project_tree.pack(expand=True, fill="both", padx=5, pady=(0,5))
        self.populate_tree("C:/Users/DC/my-bot-project", "")

        self.chat_label = tk.Label(self.left_panel, text="💬 Чати", bg="#f0f0f0", font=("Arial", 12, "bold"))
        self.chat_label.pack(pady=(10, 0))

        self.chat_list = tk.Listbox(self.left_panel)
        self.chat_list.pack(fill="both", expand=False, padx=5, pady=(0, 10))
        self.chat_list.bind("<<ListboxSelect>>", self.load_selected_chat)

        self.center_panel = tk.Frame(self.root, bg="#ffffff")
        self.center_panel.pack(side="left", fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(self.center_panel, wrap="word", height=30)
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.add_context_menu(self.chat_display)

        self.chat_display.tag_bind("gpt_action", "<Button-1>", self.on_action_click)
        self.chat_display.tag_bind("gpt_action", "<Button-3>", self.on_action_right_click)

       
        self.prompt_entry = tk.Entry(self.center_panel, font=("Arial", 12))
        self.prompt_entry.pack(fill="x", padx=10, pady=5)

        self.send_button = tk.Button(self.center_panel, text="Відправити", command=self.send_prompt)
        self.send_button.pack(padx=10, pady=(0,10))

        self.right_panel = tk.Frame(self.root, width=400, bg="#f9f9f9")
        self.right_panel.pack(side="right", fill="y")

        self.code_label = tk.Label(self.right_panel, text="👁️ Попередній код", bg="#f9f9f9", font=("Arial", 12, "bold"))
        self.code_label.pack(pady=10)

        self.code_preview = scrolledtext.ScrolledText(self.right_panel, wrap="none", height=30)
        self.code_preview.pack(fill="both", expand=True, padx=10)
        self.add_context_menu(self.code_preview)

        self.explain_button = tk.Button(self.right_panel, text="🧠 Поясни код справа", command=self.explain_code_preview)
        self.explain_button.pack(pady=5)

        self.analyze_all_button = tk.Button(self.right_panel, text="🧠 Аналізуй весь стіл", command=self.analyze_all_code)
        self.analyze_all_button.pack(pady=5)

        self.explain_last_action_button = tk.Button(
            self.right_panel,
            text="🧠 Поясни останню дію",
            command=self.explain_last_action
        )
        self.explain_last_action_button.pack(pady=5)

    def add_context_menu(self, widget):
        menu = Menu(widget, tearoff=0)
        menu.add_command(label="Копіювати", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Вставити", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Вирізати", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Виділити все", command=lambda: widget.event_generate("<<SelectAll>>"))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def explain_code_preview(self):
        code = self.code_preview.get("1.0", tk.END).strip()
        if not code:
            self.chat_display.insert(tk.END, "⚠️ Немає коду для пояснення\n\n")
            return

        try:
            client = OpenAI(api_key=API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Поясни, що робить наступний Python-код максимально стисло:"},
                    {"role": "user", "content": code}
                ],
                temperature=0.5
            )
            explanation = response.choices[0].message.content.strip()
            self.chat_display.insert(tk.END, f"🤖 Пояснення коду:\n{explanation}\n\n")
            self.chat_display.see(tk.END)

        except Exception as e:
            self.chat_display.insert(tk.END, f"❌ Помилка пояснення коду: {e}\n\n")

    def populate_tree(self, path, parent):
        for item in os.listdir(path):
            abspath = os.path.join(path, item)
            isdir = os.path.isdir(abspath)
            oid = self.project_tree.insert(parent, "end", text=item, open=False, values=(abspath,))
            if isdir:
                self.populate_tree(abspath, oid)

        self.project_tree.bind("<<TreeviewSelect>>", self.on_file_select)

    def load_chats(self):
        self.chat_list.delete(0, tk.END)
        files = sorted(os.listdir("chats"))
        for f in files:
            if f.endswith(".json"):
                self.chat_list.insert(tk.END, f)

        if not files:
            self.create_new_chat()

    def create_new_chat(self):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.current_chat_file = f"chats/chat_{timestamp}.json"
        self.chat_history = []
        self.save_chat()
        self.load_chats()
        self.chat_list.selection_set(tk.END)

    def load_selected_chat(self, event):
        selection = self.chat_list.curselection()
        if not selection:
            return
        filename = self.chat_list.get(selection[0])
        path = os.path.join("chats", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.chat_history = json.load(f)
            self.current_chat_file = path
            self.chat_display.delete("1.0", tk.END)
            for msg in self.chat_history:
                role = "👤" if msg["role"] == "user" else "🤖 GPT"
                self.chat_display.insert(tk.END, f"{role} {msg['content']}\n\n")
        except:
            self.chat_display.insert(tk.END, "⚠️ Не вдалося завантажити чат")

    def save_chat(self):
        if self.current_chat_file:
            with open(self.current_chat_file, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, indent=2, ensure_ascii=False)

    def on_file_select(self, event):
        selected = self.project_tree.focus()
        path = self.project_tree.item(selected, "values")[0]
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.current_file_content = content
                self.code_preview.delete("1.0", tk.END)
                self.code_preview.insert(tk.END, content)
            except Exception as e:
                self.code_preview.delete("1.0", tk.END)
                self.code_preview.insert(tk.END, f"⚠️ Не вдалося відкрити файл: {e}")

    def send_prompt(self):
        user_input = self.prompt_entry.get()
        if not user_input.strip():
            return

        self.chat_display.insert(tk.END, f"👤 {user_input}\n")
        self.chat_history.append({"role": "user", "content": user_input})

        try:
            response_json = interpret_user_prompt(user_input, context_code=self.current_file_content, return_data=True)

            # 🆔 Генеруємо ID для дії
            history_id = f"id_{self.action_counter:03}"
            assistant_msg = f"GPT: Згенеровано дію ✅ [{history_id}]"
            self.action_counter += 1

            # 💾 Зберігаємо цей ID як останню дію
            self.last_action_id = history_id

            self.chat_display.insert(tk.END, f"🤖 {assistant_msg}\n", "gpt_action")
            self.chat_history.append({"role": "assistant", "content": assistant_msg})

            if response_json:
                code = response_json.get("code") or response_json.get("content")
                if code:
                    self.code_preview.delete("1.0", tk.END)
                    self.code_preview.insert(tk.END, code)

                # 🧩 Генеруємо унікальний ID для команди
                history_id = f"cmd_{self.command_counter:03}"
                response_json["history_id"] = history_id

                # ✅ Додаємо також посилання на останню дію для rollback
                if self.last_action_id:
                    response_json["target_id"] = self.last_action_id

                with open("cache.txt", "w", encoding="utf-8") as f:
                    f.write(json.dumps(response_json, indent=2, ensure_ascii=False))

                self.chat_display.insert(tk.END, f"📩 [{history_id}] Команду записано в cache.txt\n", "gpt_action")
                self.command_counter += 1
                
                save_to_memory(response_json)  # 💾 Зберігаємо повну команду з code/content

                result = handle_command(response_json)
                self.chat_display.insert(tk.END, f"📤 Виконано: {result.get('message', '⛔ Невідома відповідь')}\n")
                self.chat_history.append({"role": "assistant", "content": result.get('message', '⛔ Невідома відповідь')})

        except Exception as e:
            self.chat_display.insert(tk.END, f"❌ Помилка GPT: {e}\n")
            self.chat_history.append({"role": "assistant", "content": f"❌ Помилка GPT: {e}"})

        self.chat_display.insert(tk.END, "\n")
        self.chat_display.see(tk.END)
        self.prompt_entry.delete(0, tk.END)
        self.save_chat()

    def on_action_click(self, event):
        index = self.chat_display.index(f"@{event.x},{event.y}")
        line = self.chat_display.get(index + " linestart", index + " lineend")

        self.code_preview.delete("1.0", tk.END)
        self.code_preview.insert(tk.END, f"🔍 Ви обрали дію:\n{line}\n\n")

        # Підсвітити рядок
        self.chat_display.tag_remove("highlighted", "1.0", tk.END)
        self.chat_display.tag_add("highlighted", index + " linestart", index + " lineend")
        self.chat_display.tag_configure("highlighted", background="#d0ebff")

        # Витягнути history_id
        if "[" in line and "]" in line:
            start = line.find("[") + 1
            end = line.find("]")
            history_id = line[start:end]
        else:
            history_id = None

        # Показати код з історії
        if history_id:
            cmd = get_command_by_id(history_id)
            if cmd:
                content = cmd.get("code") or cmd.get("content") or ""
                if content:
                    self.code_preview.insert(tk.END, f"\n📦 Код з ID {history_id}:\n{content}")

    def on_action_right_click(self, event):
        index = self.chat_display.index(f"@{event.x},{event.y}")
        selected_line = self.chat_display.get(index + " linestart", index + " lineend").strip()

        # Витягнути history_id з рядка (якщо є)
        if "[" in selected_line and "]" in selected_line:
            start = selected_line.find("[") + 1
            end = selected_line.find("]")
            target_id = selected_line[start:end]
        else:
            target_id = None

        def rollback_action():
            if not target_id:
                self.chat_display.insert(tk.END, "⚠️ Неможливо визначити history_id для відкату\n")
                return
            try:
                command = {"action": "undo_change", "target_id": target_id}
                with open("cache.txt", "w", encoding="utf-8") as f:
                    f.write(json.dumps(command, indent=2, ensure_ascii=False))
                result = handle_command(command)
                self.chat_display.insert(tk.END, f"🔁 Відкат {target_id}: {result.get('message', '⛔ Помилка')}\n", "gpt_action")
            except Exception as e:
                self.chat_display.insert(tk.END, f"❌ Помилка відкату: {e}\n", "gpt_action")

        def delete_action():
            self.chat_display.insert(tk.END, f"🗑️ Видалено дію: {selected_line}\n")

        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="⏪ Відкотити", command=rollback_action)
        menu.add_command(label="❌ Видалити", command=delete_action)
        menu.tk_popup(event.x_root, event.y_root)

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3", show_menu)

    def explain_last_action(self):
        if not hasattr(self, "last_action_id") or not self.last_action_id:
            self.chat_display.insert(tk.END, "⚠️ Немає останньої дії для пояснення\n")
            return

        try:
            with open(".ben_memory.json", "r", encoding="utf-8") as f:
                memory = json.load(f)

            # Знаходимо команду за last_action_id
            cmd = next((item for item in reversed(memory) if item.get("history_id") == self.last_action_id), None)
            if not cmd:
                self.chat_display.insert(tk.END, f"⚠️ Команду не знайдено: {self.last_action_id}\n")
                return

            code = cmd.get("code") or cmd.get("content")
            if not code:
                self.chat_display.insert(tk.END, f"⚠️ Немає коду для пояснення\n")
                return

            client = OpenAI(api_key=API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Поясни, що робить цей Python-код стисло й зрозуміло:"},
                    {"role": "user", "content": code}
                ],
                temperature=0.4
            )

            explanation = response.choices[0].message.content.strip()
            self.chat_display.insert(tk.END, f"🧠 Пояснення останньої дії:\n{explanation}\n\n")
            self.chat_display.see(tk.END)

        except Exception as e:
            self.chat_display.insert(tk.END, f"❌ Помилка пояснення: {e}\n")
    
    def analyze_all_code(self):
        base_dir = os.path.abspath("..")
        all_code = ""
        scanned_files = []

        for root_dir, _, files in os.walk(base_dir):
            if any(x in root_dir for x in ["__pycache__", ".git", "venv"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root_dir, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            relative = os.path.relpath(file_path, base_dir)
                            all_code += f"# Файл: {relative}\n{content}\n\n"
                            scanned_files.append(relative)
                    except:
                        continue

        if not all_code.strip():
            self.chat_display.insert(tk.END, "⚠️ Немає .py файлів для аналізу\n\n")
            return

        # 🔎 Записуємо лог про сканування
        log_path = os.path.join(base_dir, "debug.log")
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"[GPT] 🔍 Скановано {len(scanned_files)} файлів:\n")
            for name in scanned_files:
                log.write(f" - {name}\n")

        try:
            client = OpenAI(api_key=API_KEY)
            analyzing = True
            iteration = 1

            while analyzing:
                self.chat_display.insert(tk.END, f"🔎 GPT: Аналіз ітерація {iteration}...\n")
                self.chat_display.see(tk.END)

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Проаналізуй наведений код. Якщо все добре — напиши '✅ Все добре'. Якщо є помилки — згенеруй JSON-команду у форматі Ben для їх виправлення."},
                        {"role": "user", "content": all_code}
                    ],
                    temperature=0.4
                )

                result = response.choices[0].message.content.strip()
                self.chat_display.insert(tk.END, f"🤖 GPT:\n{result}\n\n")
                self.chat_display.see(tk.END)

                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"[GPT] 📊 Результат ітерації {iteration}:\n{result}\n\n")

                if "✅" in result:
                    analyzing = False
                    break

                try:
                    command = json.loads(result)
                    with open("cache.txt", "w", encoding="utf-8") as f:
                        f.write(json.dumps(command, indent=2, ensure_ascii=False))
                    exec_result = handle_command(command)
                    self.chat_display.insert(tk.END, f"📤 Виконано: {exec_result.get('message', '⛔ Невідома відповідь')}\n\n")
                    self.chat_display.see(tk.END)
                except Exception as e:
                    self.chat_display.insert(tk.END, f"❌ Помилка JSON-команди або її виконання: {e}\n\n")
                    break

                time.sleep(1)
                iteration += 1

        except Exception as e:
            self.chat_display.insert(tk.END, f"❌ Помилка аналізу GPT: {e}\n\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = BenAssistantGUI(root)
    root.mainloop()
