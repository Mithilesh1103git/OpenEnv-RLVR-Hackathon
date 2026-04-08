import json
import os
from pathlib import Path

import dotenv
import jsonschema
import requests
from dotenv import load_dotenv
from jsonschema import Draft7Validator

env_file_name = ".env"
env_dir = Path(__file__).parent.parent.resolve()
env_file_path = f"{env_dir}/{env_file_name}"
try:
    env = dotenv.dotenv_values(env_file_path)
    brand_name_env_var = env.get("BRAND_NAME")
    lms_link_env_var = env.get("LMS_LINK")
except:
    load_dotenv(env_file_path)
    brand_name_env_var = os.environ["BRAND_NAME"]
    lms_link_env_var = os.environ["LMS_LINK"]


env_file_name = "validation_schema.json"
env_dir = Path(__file__).parent.parent.resolve()
message_schema_file_path = f"{env_dir}/{env_file_name}"


def parse_llm_response(message: str):

    data_validation = {}

    parsed_dict = {
        "is_present": {
            "brand_name": False,
            "greetings": False,
            "greetings_prefix": False,
            "greetings_username": False,
            "message": False,
            "details": False,
            "assignment_title": False,
            "deadline": False,
            "lms_link": False,
            "associated_lecture_link": False,
            "youtube_lecture_link": False,
        },
        "raw_values": [],
    }

    root_dict_node = message["notification"]
    if not root_dict_node:
        return parsed_dict

    sample_dict_keys = ["brand_name", "greetings", "message", "details"]

    for key in sample_dict_keys:

        if key == "brand_name":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["brand_name"] = True
                parsed_dict["raw_values"].append({"brand_name": main_key_node})
            if main_key_node == brand_name_env_var:
                data_validation["brand_name"] = True

        if key == "greetings":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["greetings"] = True

                greetings_prefix = main_key_node["prefix"]
                if greetings_prefix:
                    parsed_dict["is_present"]["greetings_prefix"] = True
                    parsed_dict["raw_values"].append(
                        {"greetings_prefix": greetings_prefix}
                    )

                greetings_username = main_key_node["username"]
                if greetings_prefix:
                    parsed_dict["is_present"]["greetings_username"] = True
                    parsed_dict["raw_values"].append(
                        {"greetings_username": greetings_username}
                    )

        if key == "message":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["message"] = True
                parsed_dict["raw_values"].append({"message": main_key_node})

        if key == "details":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["details"] = True

                for detail in main_key_node:

                    detail_detail_category = detail["category"]
                    detail_type = detail["type"]
                    detail_key = detail["label"]
                    detail_value = detail["value"]

                    if detail_type == "assignment_title":
                        parsed_dict["is_present"]["assignment_title"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type == "deadline":
                        parsed_dict["is_present"]["deadline"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type == "lms_link":
                        if (
                            lms_link_env_var is not None
                            and lms_link_env_var in detail_value
                        ):
                            parsed_dict["is_present"]["lms_link"] = True
                            parsed_dict["raw_values"].append({detail_key: detail_value})
                            data_validation[detail_type] = True
                    if detail_type == "associated_lecture_link":
                        parsed_dict["is_present"]["associated_lecture_link"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                        try:
                            response = requests.head(detail_value, timeout=5)
                            if response.status_code < 400:
                                data_validation[detail_type] = True
                        except:
                            data_validation[detail_type] = False
                    if detail_type == "youtube_lecture_link":
                        if "https://www.youtube.com" in detail_value:
                            parsed_dict["is_present"]["youtube_lecture_link"] = True
                            parsed_dict["raw_values"].append({detail_key: detail_value})
                            try:
                                response = requests.head(detail_value, timeout=5)
                                if response.status_code < 400:
                                    data_validation[detail_type] = True
                            except:
                                data_validation[detail_type] = False

    parsed_dict["data_validation"] = data_validation

    return parsed_dict


def reward_collection(parsed_dict: dict):
    rewards_collected = []
    observations = []

    is_present_keys = parsed_dict["is_present"].keys()
    for key in list(is_present_keys):
        is_present_value = parsed_dict["is_present"][key]
        if is_present_value:
            is_present_reward = 0.5
            rewards_collected.append(is_present_reward)
            observations.append(
                f"Element '{key}_is_present' found in message, therefore reward of {is_present_reward} was given."
            )

    data_validation_keys = parsed_dict["data_validation"].keys()
    for key in list(data_validation_keys):
        data_validation_value = parsed_dict["data_validation"][key]
        if data_validation_value:
            data_validation_reward = 1
            rewards_collected.append(data_validation_reward)
            observations.append(
                f"Element '{key}_data_validation' found in message, therefore reward of {data_validation_reward} was given."
            )

    return rewards_collected, observations


def get_final_reward(message: str):
    message = json.loads(message)
    print(message)

    message_schema = {}
    with open(message_schema_file_path, "r+") as file:
        message_schema = json.load(file)
        # print(message_schema)

    final_reward = -1
    observations = [
        {
            "Exception": "Input message json schema validation failed. Therefore no rewards given."
        }
    ]
    if isinstance(message, dict):
        try:
            validator = Draft7Validator(message_schema)
            validation_result = validator.validate(message)
            if validation_result == None:
                parsed_dict = parse_llm_response(message)
                rewards_collected, observations = reward_collection(parsed_dict)
                final_reward = sum(rewards_collected)
        except jsonschema.exceptions.ValidationError:
            print("Schema validation failed.")

    return final_reward, observations
