import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess

class GitLogViewer(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="🕘 Git Log").pack(anchor="w")
        self.text_area = scrolledtext.ScrolledText(self, height=10, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        refresh_btn = ttk.Button(self, text="🔄 Оновити Git Log", command=self.load_git_log)
        refresh_btn.pack(pady=5)

    def load_git_log(self):
        try:
            output = subprocess.check_output(["git", "log", "-n", "10", "--oneline"], stderr=subprocess.STDOUT, text=True)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert(tk.END, output)
            self.text_area.see(tk.END)
        except subprocess.CalledProcessError as e:
            self.text_area.insert(tk.END, f"❌ Git Error: {e.output}\n")