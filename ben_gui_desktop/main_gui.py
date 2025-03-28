import tkinter as tk
from tkinter import ttk
from widgets.action_selector import ActionSelector
from tkinter import scrolledtext
import os
from widgets.history_viewer import HistoryViewer
import json

from widgets.parameter_form import ParameterForm
def on_action_change(action):
    print("🔄 Action changed to:", action)

root = tk.Tk()
root.title("Ben GUI Interface")
root.geometry("600x400")

ttk.Label(root, text="Ben Assistant GUI", font=("Arial", 16)).pack(pady=10)
history_memory = HistoryViewer(root, "🧠 Історія .ben_memory.json")
history_memory.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

history_sqlite = HistoryViewer(root, "📜 Історія з SQLite")
history_sqlite.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

parameter_form = ParameterForm(root)
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
status_label = ttk.Label(root, text="🟡 Перевірка статусу агента...")
status_label.pack(pady=5)
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
def send_command():
    command = {
        "action": action_selector.get_selected_action()
    }
    command.update(parameter_form.get_command_fields())

    with open(request_file, "w", encoding="utf-8") as f:
        json.dump([command], f, indent=2)

    print("📤 Відправлено:", command)

send_button = ttk.Button(root, text="📩 Надіслати команду", command=send_command)
send_button.pack(pady=10)
action_selector = ActionSelector(root, on_action_change)
action_selector.pack(fill=tk.X, padx=20, pady=10)

root.mainloop()