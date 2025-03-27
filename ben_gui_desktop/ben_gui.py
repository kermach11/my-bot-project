import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import os

CACHE_FILE = "cache.txt"

class BenGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ben Assistant GUI")

        self.input_label = tk.Label(root, text="Введіть JSON-команду")
        self.input_label.pack()

        self.input_box = scrolledtext.ScrolledText(root, height=10, width=80)
        self.input_box.pack()

        self.send_button = tk.Button(root, text="▶️ Надіслати", command=self.send_command)
        self.send_button.pack(pady=4)

        self.undo_button = tk.Button(root, text="↩️ Undo", command=lambda: self.send_simple("undo_change"))
        self.undo_button.pack(pady=2)

        self.repeat_button = tk.Button(root, text="🔁 Repeat", command=lambda: self.send_simple("repeat_last"))
        self.repeat_button.pack(pady=2)

        self.output_label = tk.Label(root, text="Останні команди")
        self.output_label.pack(pady=4)

        self.history_box = scrolledtext.ScrolledText(root, height=10, width=80, state="disabled")
        self.history_box.pack()

    def send_simple(self, action):
        command = {"action": action}
        self.write_cache([command])
        self.append_history(json.dumps(command, ensure_ascii=False))

    def send_command(self):
        try:
            text = self.input_box.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("Увага", "Поле введення порожнє")
                return
            command = json.loads(text)
            if not isinstance(command, list):
                command = [command]
            self.write_cache(command)
            self.append_history(text)
            self.input_box.delete("1.0", tk.END)
        except Exception as e:
            messagebox.showerror("Помилка", f"❌ Невірний JSON: {str(e)}")

    def write_cache(self, data):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def append_history(self, text):
        self.history_box.configure(state="normal")
        self.history_box.insert(tk.END, text + "\n\n")
        self.history_box.configure(state="disabled")

if __name__ == "__main__":
    if not os.path.exists("ben_gui_desktop"):
        os.makedirs("ben_gui_desktop")

    root = tk.Tk()
    gui = BenGUI(root)
    root.mainloop()
        self.list_button = tk.Button(root, text="📄 List Files", command=lambda: self.send_simple("list_files"))
        self.list_button.pack(pady=2)