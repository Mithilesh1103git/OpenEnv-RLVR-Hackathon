import json
import os
from pathlib import Path

import dotenv
import jsonschema
import requests
from dotenv import dotenv_values, load_dotenv
from jsonschema import Draft7Validator

try:
    from ..models import EdupilotRewards, EdupilotMetrics
except ImportError:
    from models import EdupilotRewards, EdupilotMetrics


env_file_name = ".env"
env_dir = Path(__file__).parent.parent.resolve()
env_file_path = f"{env_dir}/{env_file_name}"
load_dotenv(dotenv_path=env_file_path)

BRAND_NAME_ENV_VAR = os.getenv("BRAND_NAME", "Default Brand")
STATIC_MESSAGE_TEXT = os.getenv("STATIC_MESSAGE_TEXT", "Default Message")
LMS_DOMAIN_URL = os.getenv("LMS_DOMAIN_URL")
YOUTUBE_DOMAIN_URL = os.getenv("YOUTUBE_DOMAIN_URL")


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

    root_dict_node = {}
    try:
        root_dict_node = message["notification"]
        if not root_dict_node:
            return parsed_dict
    except:
        pass

    sample_dict_keys = ["brand_name", "greetings", "message", "details"]

    for key in sample_dict_keys:

        if key == "brand_name":
            try:
                main_key_node = root_dict_node[key]
                if main_key_node:
                    parsed_dict["is_present"]["brand_name"] = True
                    parsed_dict["raw_values"].append({"brand_name": main_key_node})
                if main_key_node == BRAND_NAME_ENV_VAR:
                    data_validation["brand_name"] = True
            except:
                pass

        if key == "greetings":
            try:
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
            except:
                pass

        if key == "message":
            try:
                main_key_node = root_dict_node[key]
                if main_key_node:
                    parsed_dict["is_present"]["message"] = True
                    parsed_dict["raw_values"].append({"message": main_key_node})
                    if STATIC_MESSAGE_TEXT is not None and main_key_node.startswith(
                        STATIC_MESSAGE_TEXT
                    ):
                        data_validation["message"] = True
            except:
                pass

        if key == "details":
            try:
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
                            parsed_dict["is_present"]["lms_link"] = True
                            parsed_dict["raw_values"].append({detail_key: detail_value})
                            if LMS_DOMAIN_URL is not None and detail_value.startswith(
                                LMS_DOMAIN_URL
                            ):
                                data_validation[detail_type] = True
                        if detail_type == "associated_lecture_link":
                            parsed_dict["is_present"]["associated_lecture_link"] = True
                            parsed_dict["raw_values"].append({detail_key: detail_value})
                            if LMS_DOMAIN_URL is not None and detail_value.startswith(
                                LMS_DOMAIN_URL
                            ):
                                try:
                                    response = requests.head(detail_value, timeout=5)
                                    if response.status_code < 400:
                                        data_validation[detail_type] = True
                                except:
                                    data_validation[detail_type] = False
                        if detail_type == "youtube_lecture_link":
                            parsed_dict["is_present"]["youtube_lecture_link"] = True
                            parsed_dict["raw_values"].append({detail_key: detail_value})
                            if (
                                YOUTUBE_DOMAIN_URL is not None
                                and detail_value.startswith(YOUTUBE_DOMAIN_URL)
                            ):
                                try:
                                    response = requests.head(detail_value, timeout=5)
                                    if response.status_code < 400:
                                        data_validation[detail_type] = True
                                except:
                                    data_validation[detail_type] = False
            except:
                pass

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
                f"Observed successful schema validation of element '{key}' and therefore, reward of {is_present_reward} was given."
            )

    data_validation_keys = parsed_dict["data_validation"].keys()
    for key in list(data_validation_keys):
        data_validation_value = parsed_dict["data_validation"][key]
        if data_validation_value:
            data_validation_reward = 1
            rewards_collected.append(data_validation_reward)
            observations.append(
                f"Observed successful data validation of element '{key}' and therefore, reward of {data_validation_reward} was given."
            )

    return rewards_collected, observations


def get_rewards(message: str):
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

    return EdupilotRewards(total_reward=final_reward, reward_observations=observations)


def get_metrics(final_reward: float, edupilot_benchmark: float, history: list):
    success_ratio, mean_performance = 0.0, 0.0

    if final_reward and edupilot_benchmark:
        current_success_ratio = final_reward / edupilot_benchmark

    len_history = len(history)
    if len_history > 1:
        mean_performance = (
            sum([history[n]["final_reward"] for n in range(len_history)]) / len_history
        )

    return EdupilotMetrics(
        benchmark=edupilot_benchmark,
        current_reward=final_reward,
        success_ratio=current_success_ratio,
        mean_performance=mean_performance,
    )
