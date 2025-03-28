import tkinter as tk
from tkinter import ttk
from widgets.action_selector import ActionSelector
from tkinter import scrolledtext
import os
from widgets.git_log_viewer import GitLogViewer
from template_manager import render_template
from widgets.user_profile_panel import UserProfilePanel
from widgets.template_editor import TemplateEditor
from widgets.history_viewer import HistoryViewer
from widgets.macro_builder import MacroBuilder

import json

from widgets.parameter_form import ParameterForm

def filter_history_entries(entries, filter_type):
    if filter_type == "all":
        return entries
    elif filter_type == "commands":
        return [e for e in entries if e.get("action")]
    elif filter_type == "errors":
        return [e for e in entries if e.get("status") == "error"]
    elif filter_type == "system":
        return [e for e in entries if not e.get("action") and not e.get("status")]
    return entries

def on_action_change(action):
    user_profile = UserProfilePanel(root)
    user_profile.pack(fill=tk.X, padx=20, pady=10)

    template_editor = TemplateEditor(root)
    template_editor.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

    print("🔄 Action changed to:", action)

root = tk.Tk()
root.title("Ben GUI Interface")
root.geometry("600x400")

ttk.Label(root, text="Ben Assistant GUI", font=("Arial", 16)).pack(pady=10)
history_memory = HistoryViewer(root, "🧠 Історія .ben_memory.json")
git_log = GitLogViewer(root)
git_log.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
history_memory.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

history_sqlite = HistoryViewer(root, "📜 Історія з SQLite")
history_sqlite.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

def insert_from_template():
    action = action_selector.get_selected_action()
    fields = parameter_form.get_command_fields()
    template_name = f"{action}.j2"
    rendered = render_template(template_name, fields)

    # 🛡️ Автовалідатор JSON
    try:
        parsed = json.loads(rendered)
    except json.JSONDecodeError as e:
        response_area.insert(tk.END, f"❌ Невірний шаблон {template_name}:\n{e}\n")
        response_area.see(tk.END)
        return

    # ✅ Якщо JSON валідний — вставити у форму
    parameter_form.entries.get("filename", ttk.Entry()).delete(0, tk.END)
    parameter_form.entries.get("filename", ttk.Entry()).insert(0, parsed.get("filename", ""))
    parameter_form.entries.get("content", ttk.Entry()).delete(0, tk.END)
    parameter_form.entries.get("content", ttk.Entry()).insert(0, parsed.get("content", ""))
    response_area.insert(tk.END, f"🧩 Застосовано шаблон {template_name}\n")
    response_area.see(tk.END)

insert_tpl_btn = ttk.Button(root, text="🧩 Insert from Template", command=insert_from_template)
insert_tpl_btn.pack(pady=5)

import ast
parameter_form = ParameterForm(root)
def check_duplicate_function():
    content = parameter_form.get_command_fields().get("content")
    filename = parameter_form.get_command_fields().get("filename")
    if not content or not filename:
        response_area.insert(tk.END, "⚠️ Потрібно вказати content і filename\n")
        return
    try:
        new_ast = ast.parse(content)
        new_func_name = next((n.name for n in ast.walk(new_ast) if isinstance(n, ast.FunctionDef)), None)
        if not new_func_name:
            response_area.insert(tk.END, "⚠️ Не знайдено імʼя функції у content\n")
            return

        file_path = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(file_path):
            response_area.insert(tk.END, "ℹ️ Файл не існує, дублювання неможливе\n")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            existing_ast = ast.parse(f.read())
        for node in ast.walk(existing_ast):
            if isinstance(node, ast.FunctionDef) and node.name == new_func_name:
                response_area.insert(tk.END, f"⚠️ Функція '{new_func_name}' вже існує в '{filename}'\n")
                return
        response_area.insert(tk.END, f"✅ Функція '{new_func_name}' відсутня в '{filename}' — можна вставляти\n")
    except Exception as e:
        response_area.insert(tk.END, f"❌ Error: {e}\n")

check_btn = ttk.Button(root, text="🧠 Перевірити функцію на дубль", command=check_duplicate_function)
check_btn.pack(pady=5)
def refresh_history():
    cmds = [
        {"action": "list_history"},
        {"action": "view_sql_history"}
    ]
    with open(request_file, "w", encoding="utf-8") as f:
        json.dump(cmds, f, indent=2)

    def load():
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                try:
                    responses = json.load(f)
                    history_memory.update_history(responses[0].get("history", []))
                    history_sqlite.update_history(responses[1].get("history", []))
                except Exception as e:
                    response_area.insert(tk.END, f"❌ Error loading history: {e}\n")
    root.after(1500, load)

refresh_btn = ttk.Button(root, text="🔁 Оновити історію", command=refresh_history)
refresh_btn.pack(pady=5)
response_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10)
response_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

macro_builder = MacroBuilder(root, response_area)
macro_builder.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

# [BEN-ANCHOR: run_macro_button]
run_macro_btn = ttk.Button(root, text="▶️ Запустити макрос", command=macro_builder.run_macro)
run_macro_btn.pack(pady=5)
# [BEN-ANCHOR-END]

status_label = ttk.Label(root, text="🟡 Перевірка статусу агента...")
status_label.pack(pady=5)
request_file = "request.json"
response_file = "gpt_response.json"

def test_python_file():
    filename = parameter_form.get_command_fields().get("filename")
    if not filename:
        response_area.insert(tk.END, "⚠️ Вкажіть 'filename' для перевірки.\n")
        return
    command = {"action": "test_python", "filename": filename}
    with open(request_file, "w", encoding="utf-8") as f:
        json.dump([command], f, indent=2)
    def show_result():
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                try:
                    result = json.load(f)
                    response_area.insert(tk.END, f"🧪 Тест: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
                    response_area.see(tk.END)
                except Exception as e:
                    response_area.insert(tk.END, f"❌ Error: {e}\n")
    root.after(1000, show_result)

test_button = ttk.Button(root, text="🧪 Test Python File", command=test_python_file)
test_button.pack(pady=5)

def undo_last_change():
    filename = parameter_form.get_command_fields().get("filename")
    if not filename:
        response_area.insert(tk.END, "⚠️ Вкажіть 'filename' для відкату.\n")
        return
    cmd = {"action": "undo_change", "filename": filename}
    with open(request_file, "w", encoding="utf-8") as f:
        json.dump([cmd], f, indent=2)

    response_area.insert(tk.END, f"↩️ Відкат змін для: {filename}\n")
    response_area.see(tk.END)
    root.after(1000, load_response)

undo_btn = ttk.Button(root, text="↩️ Undo Last Change", command=undo_last_change)
undo_btn.pack(pady=5)

def check_agent_status():
    command = {"action": "check_status"}
    with open(request_file, "w", encoding="utf-8") as f:
        json.dump([command], f, indent=2)

    def update_status():
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                try:
                    response = json.load(f)[0]
                    msg = response.get("message", "❌ No response")
                    if "🟢" in msg:
                        status_label.config(text=msg)
                    else:
                        status_label.config(text=f"🔴 {msg}")
                except:
                    status_label.config(text="❌ Error reading agent status")

    root.after(1500, update_status)

check_agent_status()


def load_response():
    if os.path.exists(response_file):
        with open(response_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)

                # 🧠 Автоаналіз відхилень
                if isinstance(data, list):
                    for entry in data:
                        msg = entry.get("message", "")
                        if "❌" in msg or "⚠️" in msg:
                            response_area.insert(tk.END, f"❌ Відхилено: {msg}\n")
                else:
                    msg = data.get("message", "")
                    if "❌" in msg or "⚠️" in msg:
                        response_area.insert(tk.END, f"❌ Відхилено: {msg}\n")

                response_area.insert(tk.END, f"✅ Відповідь: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                response_area.see(tk.END)
            except Exception as e:
                response_area.insert(tk.END, f"❌ Error reading response: {e}\n")


def send_command():
    command = {
        "action": action_selector.get_selected_action()
    }
    command.update(parameter_form.get_command_fields())

    with open(request_file, "w", encoding="utf-8") as f:
        json.dump([command], f, indent=2)

    response_area.insert(tk.END, f"📤 Відправлено: {json.dumps(command, indent=2, ensure_ascii=False)}\n")
    response_area.see(tk.END)
    root.after(1000, load_response)
parameter_form.pack(fill=tk.X, padx=20, pady=10)

send_button = ttk.Button(root, text="📩 Надіслати команду", command=send_command)
send_button.pack(pady=10)
action_selector = ActionSelector(root, on_action_change)
action_selector.pack(fill=tk.X, padx=20, pady=10)

def on_close():
    if user_profile:
        user_profile.save_profile_settings()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()