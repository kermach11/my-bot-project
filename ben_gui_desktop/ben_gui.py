import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import json
import os

class BenGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧠 Ben Assistant GUI")
        self.geometry("600x400")
        self.create_widgets()

    def create_widgets(self):
        self.label = tk.Label(self, text="Введіть команду (JSON):")
        self.label.pack(pady=10)

        self.textbox = tk.Text(self, height=10)
        self.textbox.pack(padx=10, fill=tk.BOTH, expand=True)

        self.run_button = tk.Button(self, text="▶️ Запустити", command=self.run_command)
        self.run_button.pack(pady=10)

        self.output_label = tk.Label(self, text="Результат:")
        self.output_label.pack()

        self.output = tk.Text(self, height=10, bg="#f0f0f0")
        self.output.pack(padx=10, fill=tk.BOTH, expand=True)

    def run_command(self):
        try:
            command = json.loads(self.textbox.get("1.0", tk.END))
            with open("cache.txt", "w", encoding="utf-8") as f:
                json.dump(command, f, indent=2, ensure_ascii=False)

            result = subprocess.run(["python", "gpt_agent_cache.py"], capture_output=True, text=True)
            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, result.stdout)
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

if __name__ == "__main__":
    app = BenGUI()
    app.mainloop()