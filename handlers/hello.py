import json
import os

print("✅ hello.py RUNNING")

result = {"parsed_result": "Hello"}
output_path = os.path.abspath("last_result.json")
print(f"📦 Writing to: {output_path}")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f)
print("✅ DONE writing last_result.json")
