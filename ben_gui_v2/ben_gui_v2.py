import os
import tkinter as tk
from tkinter import ttk, scrolledtext

class BenAssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ben Assistant v2")
        self.root.geometry("1200x700")

        self.setup_layout()

    def setup_layout(self):
        self.left_panel = tk.Frame(self.root, width=250, bg="#f0f0f0")
        self.left_panel.pack(side="left", fill="y")

        self.project_label = tk.Label(self.left_panel, text="🗂️ Стіл", bg="#f0f0f0", font=("Arial", 12, "bold"))
        self.project_label.pack(pady=10)

        self.project_tree = ttk.Treeview(self.left_panel)
        self.project_tree.pack(expand=True, fill="both", padx=5)
        self.populate_tree(".", "")

        self.center_panel = tk.Frame(self.root, bg="#ffffff")
        self.center_panel.pack(side="left", fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(self.center_panel, wrap="word", height=30)
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(10, 0))

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

    def populate_tree(self, path, parent):
        for item in os.listdir(path):
            abspath = os.path.join(path, item)
            isdir = os.path.isdir(abspath)
            oid = self.project_tree.insert(parent, "end", text=item, open=False)
            if isdir:
                self.populate_tree(abspath, oid)

    def send_prompt(self):
        user_input = self.prompt_entry.get()
        if not user_input.strip():
            return
        self.chat_display.insert(tk.END, f"👤 {user_input}\n")
        self.chat_display.insert(tk.END, f"🤖 GPT: (відповідь тут буде...)\n\n")
        self.chat_display.see(tk.END)
        self.prompt_entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = BenAssistantGUI(root)
    root.mainloop()
