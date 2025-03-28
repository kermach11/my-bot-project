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

action_selector = ActionSelector(root, on_action_change)
action_selector.pack(fill=tk.X, padx=20, pady=10)

root.mainloop()