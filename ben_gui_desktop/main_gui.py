def enable_ctrl_shortcuts(widget):
    widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
    widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
    widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>"))

def apply_shortcuts_recursively(widget):
    if isinstance(widget, (tk.Entry, tk.Text, scrolledtext.ScrolledText)):
        enable_ctrl_shortcuts(widget)
    if hasattr(widget, "winfo_children"):
        for child in widget.winfo_children():
            apply_shortcuts_recursively(child)

# Включити гарячі клавіші для всіх віджетів
apply_shortcuts_recursively(scrollable_frame)
