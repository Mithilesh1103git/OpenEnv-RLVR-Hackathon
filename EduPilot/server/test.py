import json
import jsonschema
from jsonschema import Draft7Validator

message = """
{
  "notification": {
    "brand_name": "Masai School",
    "greetings": {
      "prefix": "Dear",
      "username": "Mithilesh Nakade"
    },
    "message": "A new assignment has been released for you.",
    "details": [
      {
        "category": "main-details",
        "type": "assignment_title",
        "label": "📘 Assignment Title:",
        "value": "Faculty Session 87 - Object Detection & Image Segmentation"
      },
      {
        "category": "main-details",
        "type": "deadline",
        "label": "🗓 Deadline:",
        "value": "Apr 9, 2026 at 11:59 PM"
      },
      {
        "category": "extra-details",
        "type": "lms_link",
        "label": "🔗 LMS Link:",
        "value": "https://students.masaischool.com/assignments/76143"
      },
      {
        "category": "extra-details",
        "type": "associated_lecture_link",
        "label": "associated lecture:",
        "value": "https://abc"
      },
      {
        "category": "extra-details",
        "type": "youtube_lecture_link",
        "label": "Youtube link:",
        "value": "https://xyz"
      }
    ]
  }
}
"""

message = json.loads(message)

message_schema = {}
message_schema_file_path = r"EduPilot\validation_schema.json"
with open(message_schema_file_path, "r+") as file:
  message_schema = json.load(file)

if isinstance(message, dict):
  try:
    validator = Draft7Validator(message_schema)
    validation_result = validator.validate(message)
    print("Schema successfully validated.")
  except jsonschema.exceptions.ValidationError:
    print("Schema validation failed.")
else:
  final_reward = 0
  observations = {"Exception": "Input message json schema validation failed. Therefore no rewards given."}
