import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os

class TemplateEditor(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.current_template = None
        self.unsaved_changes = False

        ttk.Label(self, text="📁 Template Editor", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 5))

        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X)

        self.template_selector = ttk.Combobox(top_frame, state="readonly")
        self.template_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.template_selector.bind("<<ComboboxSelected>>", self.load_selected_template)

        ttk.Button(top_frame, text="🆕 New Template", command=self.create_new_template).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Button(top_frame, text="🔄 Refresh List", command=self.refresh_list).pack(side=tk.LEFT)

        self.editor = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=12)
        self.editor.pack(fill=tk.BOTH, expand=True, pady=5)
        self.editor.bind("<Key>", lambda e: self.set_unsaved())

        save_btn = ttk.Button(self, text="💾 Save", command=self.save_template)
        save_btn.pack(pady=5)

        self.refresh_list()
        parent.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh_list(self):
        try:
            files = [f for f in os.listdir(self.template_dir) if f.endswith(".j2")]
            self.template_selector["values"] = files
            if files:
                self.template_selector.current(0)
                self.load_selected_template()
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to load templates: {e}")

    def load_selected_template(self, event=None):
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved", "⚠️ Unsaved changes. Discard?"):
                return
        name = self.template_selector.get()
        path = os.path.join(self.template_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, content)
            self.current_template = name
            self.unsaved_changes = False
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to load: {e}")

    def save_template(self):
        if not self.current_template:
            return
        try:
            content = self.editor.get("1.0", tk.END)
            path = os.path.join(self.template_dir, self.current_template)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.unsaved_changes = False
            messagebox.showinfo("Saved", f"✅ Saved {self.current_template}")
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to save: {e}")

    def set_unsaved(self):
        self.unsaved_changes = True

    def on_close(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Exit", "⚠️ Unsaved changes. Exit anyway?"):
                return
        self.master.destroy()