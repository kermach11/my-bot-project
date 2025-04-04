import re

def clean_json_text(text):
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        # Видаляє // тільки якщо не в лапках
        in_string = False
        new_line = ""
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_string = not in_string
            if not in_string and line[i:i+2] == "//":
                break  # коментар за межами рядка — обрізаємо
            new_line += line[i]
            i += 1
        cleaned_lines.append(new_line)
    return "\n".join(cleaned_lines)
