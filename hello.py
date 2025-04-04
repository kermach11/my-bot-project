import os
import json

result = {"parsed_result": "Hello"}
output_path = os.path.join(os.path.dirname(__file__), "last_result.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f)