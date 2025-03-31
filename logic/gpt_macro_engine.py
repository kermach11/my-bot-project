import os
import json
import requests

class GPTMacroEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate_macro(self, prompt):
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You generate macro steps in JSON for code automation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5
        }

        res = requests.post(api_url, headers=headers, json=payload)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        steps = parsed.get("steps", parsed if isinstance(parsed, list) else [])
        return steps