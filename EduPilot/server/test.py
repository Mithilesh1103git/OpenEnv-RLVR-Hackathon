import json
from pathlib import Path

env_dir = Path(__file__).parent.parent.resolve()
message_schema_file_path = f"{env_dir}/validation_schema.json"
with open(message_schema_file_path, "r+") as file:
    json_data = json.load(file)
    print(json_data)
