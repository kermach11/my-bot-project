import tkinter as tk
from tkinter import ttk, scrolledtext

class HistoryViewer(ttk.Frame):
    def __init__(self, parent, label_text):
        super().__init__(parent)
        ttk.Label(self, text=label_text).pack(anchor="w")
        self.text_area = scrolledtext.ScrolledText(self, height=10, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True)

    def update_history(self, data):
        self.text_area.delete("1.0", tk.END)
        for item in data:
            self.text_area.insert(tk.END, f"{item}\n")
        self.text_area.see(tk.END)