import tkinter as tk
from tkinter import ttk
from widgets.action_selector import ActionSelector

from widgets.parameter_form import ParameterForm
def on_action_change(action):
    print("🔄 Action changed to:", action)

root = tk.Tk()
root.title("Ben GUI Interface")
root.geometry("600x400")

ttk.Label(root, text="Ben Assistant GUI", font=("Arial", 16)).pack(pady=10)

parameter_form = ParameterForm(root)
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