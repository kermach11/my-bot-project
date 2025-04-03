import re

def clean_json_text(text):
    return re.sub(r"//.*", "", text)
