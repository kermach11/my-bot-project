import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
from config import request_file, response_file

class BenGUI:
    def __init__(self, root):
        self.root = root
        root.title("Ben Assistant GUI")
        root.geometry("700x500")

        # Ввід
        self.action_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.content_var = tk.StringVar()

        ttk.Label(root, text="Action:").pack()
        ttk.Entry(root, textvariable=self.action_var).pack(fill=tk.X)

        ttk.Label(root, text="Filename (optional):").pack()
        ttk.Entry(root, textvariable=self.filename_var).pack(fill=tk.X)

        ttk.Label(root, text="Content (optional):").pack()
        ttk.Entry(root, textvariable=self.content_var).pack(fill=tk.X)

        ttk.Button(root, text="📩 Надіслати команду", command=self.send_command).pack(pady=10)

        ttk.Label(root, text="Відповідь:").pack()
        self.response_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=15)
        self.response_area.pack(fill=tk.BOTH, expand=True)

    def send_command(self):
        command = {
            "action": self.action_var.get(),
            "filename": self.filename_var.get(),
            "content": self.content_var.get()
        }
        command = {k: v for k, v in command.items() if v.strip()}
        with open(request_file, "w", encoding="utf-8") as f:
            json.dump([command], f, indent=2)
        self.response_area.insert(tk.END, f"📤 Відправлено: {json.dumps(command)}\n")
        self.response_area.see(tk.END)

        self.root.after(1000, self.load_response)

    def load_response(self):
        if os.path.exists(response_file):
            with open(response_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    self.response_area.insert(tk.END, f"✅ Відповідь: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                    self.response_area.see(tk.END)
                except Exception as e:
                    self.response_area.insert(tk.END, f"❌ Error reading response: {e}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = BenGUI(root)
    root.mainloop()