"""
Inference Script Example
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image()
                     method

- Defaults are set only for API_BASE_URL and MODEL_NAME
    (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
    MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")

- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.

  Example:
    [START] task=click-test env=miniwob model=Qwen3-VL-30B
    [STEP] step=1 action=click('123') reward=0.00 done=false error=null
    [STEP] step=2 action=fill('456','text') reward=0.00 done=false error=null
    [STEP] step=3 action=click('789') reward=1.00 done=true error=null
    [END] success=true steps=3 rewards=0.00,0.00,1.00
"""

import base64
import os
import re
import textwrap
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from ..models import EdupilotAction, EdupilotObservation
    from .client import EdupilotEnv
except ImportError:
    from models import EdupilotAction, EdupilotObservation
    from client import EdupilotEnv

import asyncio
import json
import random

from dotenv import dotenv_values, load_dotenv
from openai import OpenAI
from PIL import Image

env_file_name = ".env"
env_dir = Path(__file__).parent.resolve()
env_file_path = f"{env_dir}/{env_file_name}"
load_dotenv(env_file_path)

# env_file_name = "sample_schema.json"
# env_dir = Path(__file__).parent.resolve()
# message_schema_file_path = f"{env_dir}/{env_file_name}"
# message_schema = {}
# with open(message_schema_file_path, "r+") as file:
#     message_schema = json.load(file)

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen3-VL-30B-A3B-Instruct:novita"
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
TASK_NAME = os.getenv("EDUPILOT_TASK_NAME", "unknown-task")
BENCHMARK = os.getenv("EDUPILOT_BENCHMARK", "unknown-env")
MAX_STEPS = 3
MAX_DOM_CHARS = 3500
TEMPERATURE = 0.2
MAX_TOKENS = 200
FALLBACK_ACTION = "noop()"

DEBUG = True
ACTION_PREFIX_RE = re.compile(
    r"^(action|next action)\s*[:\-]\s*",
    re.IGNORECASE,
)
ACTION_PATTERN = re.compile(r"[A-Za-z_]+\s*\(.*\)", re.DOTALL)


SYSTEM_PROMPT = textwrap.dedent("""
    You are an intelligent agent and a structured data generator.

    Your task is to produce a valid JSON object that strictly adheres to the provided notification schema and notification instance.

    Instructions:
    - If the task is to create or transform data → output ONLY valid JSON.

    Rules:
    - Output ONLY valid JSON.
    - This valid JSON has to in format that can be parsed programmatically.
    - Do not include explanations, comments, or extra text.
    - Follow the schema exactly (keys, nesting, and structure).
    - Preserve all provided values unless instructed otherwise.
    - Ensure proper formatting (double quotes, valid syntax).
    - Never mix JSON and actions.
    - No explanations or extra text.
    - Follow the schema strictly when generating JSON.
    - Keep the values in 'extra-details' in the final JSON labels etc. as they are in the details section of given notification schema and notification instance.
    - Labels should be string and should not contain any link.
    - Convert deadline in hh:mm AM/PM format.
    - If unsure:
        - For JSON tasks → best-effort valid JSON
    """).strip()

JSON_PARSER_SYSTEM_PROMPT = """
    You are intelligent schema parser and serializer-deserializer. Convert the user input into required format.
    Rules:
        - Output ONLY valid JSON.
        - Do not include explanations, comments, or extra text.
        - Follow the schema exactly (keys, nesting, and structure).
        - Preserve all provided values unless instructed otherwise.
        - Ensure proper formatting (double quotes, valid syntax).
        - No explanations or extra text.
        - Follow the schema strictly when generating JSON.
    """

notification_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Notification",
    "type": "object",
    "required": ["notification"],
    "properties": {
        "notification": {
            "type": "object",
            "required": ["brand_name", "greetings", "message", "details"],
            "properties": {
                "brand_name": {"type": "string"},
                "message": {"type": "string"},
                "greetings": {
                    "type": "object",
                    "required": ["prefix", "username"],
                    "properties": {
                        "prefix": {"type": "string"},
                        "username": {"type": "string"},
                    },
                },
                "details": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["category", "type", "label", "value"],
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["main-details", "extra-details"],
                            },
                            "type": {
                                "type": "string",
                                "enum": [
                                    "assignment_title",
                                    "deadline",
                                    "lms_link",
                                    "associated_lecture_link",
                                    "youtube_lecture_link",
                                ],
                            },
                            "label": {"type": "string"},
                            "value": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
}

notification_instance = {
    "notification": {
        "brand_name": "Scaler School",
        "greetings": {"prefix": "Dear", "username": "Mithilesh"},
        "message": "A new assignment has been released for you.",
        "details": [
            {
                "category": "main-details",
                "type": "assignment_title",
                "label": "📘 Assignment Title:",
                "value": "Faculty Session - Meta and Scaler OpenEnv Hackathon",
            },
            {
                "category": "main-details",
                "type": "deadline",
                "label": "🗓 Deadline:",
                "value": "Apr 9, 2026 at 11:59 PM",
            },
            {
                "category": "extra-details",
                "type": "lms_link",
                "label": "🔗 LMS Link:",
                "value": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/",
            },
            {
                "category": "extra-details",
                "type": "associated_lecture_link",
                "label": "associated lecture:",
                "value": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/dashboard?utm_source=midfunnel&utm_medium=email&utm_campaign=registration_acknowledgement",
            },
            {
                "category": "extra-details",
                "type": "youtube_lecture_link",
                "label": "Youtube link:",
                "value": "https://www.youtube.com/watch?v=kkCNMz0Ptd8&t=1703s",
            },
        ],
    }
}


class PromptContextModel(BaseModel):
    username: str = Field(default="Mithilesh", description="username")
    task: str = Field(
        default="I want to send an assignment reminder email to the students. All the details should be in the final notification JSON.",
        description="",
    )
    assignment_title: str = Field(default="", description="assignment title")
    deadline: str = Field(default="", description="assignment deadline")
    associated_lecture_link: str = Field(default="", description="assignment deadline")
    additional_task: str = Field(
        default="please find just one relevant youtube link for the this assignment",
        description="assignment deadline",
    )


prompt_context_list = [
    PromptContextModel(
        username="Mithilesh",
        task="I want to send an assignment reminder email to the students. All the details should be in the final notification JSON.",
        assignment_title="Meta and Scaler OpenEnv Hackathon",
        deadline="April 12, 2026 by end of the day",
        associated_lecture_link="https://www.scaler.com/school-of-technology/meta-pytorch-hackathon",
        additional_task="Find just one relevant youtube link for the subject of OpenEnv Reinforcement Learning for models and agents. Add that just one link in the value of final JSON.",
    ),
    PromptContextModel(
        username="Silvakumar",
        task="I want to send an assignment reminder email to the students. All the details should be in the final notification JSON.",
        assignment_title="NLP and Text Embeddings",
        deadline="May 14, 2026 by end of the day",
        associated_lecture_link="https://www.scaler.com/school-of-technology/meta-pytorch-hackathon",
        additional_task="Find just one relevant youtube link for the subject of NLP and Text Embeddings for models and agents. Add that just one link in the value of final JSON.",
    ),
    PromptContextModel(
        username="Ganesh",
        task="I want to send an assignment reminder email to the students. All the details should be in the final notification JSON.",
        assignment_title="CNN and RNN",
        deadline="June 25, 2026 by end of the day",
        associated_lecture_link="https://www.scaler.com/school-of-technology/meta-pytorch-hackathon",
        additional_task="Find just one relevant youtube link for the subject of CNN and RNN for models and agents. Add that just one link in the value of final JSON.",
    ),
]


client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


def call_openai_inference(client: OpenAI, model_name: str, prompt_messages: list, temperature: str, max_tokens: str):
    "Call OpenAI API endpoint for inference."
    completion = client.chat.completions.create(
        model=model_name,
        messages=prompt_messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        stream=False,
    )
    response_text = completion.choices[0].message.content

    return response_text


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True,
    )


def build_history_lines(history: List[str]) -> str:
    if not history:
        return "None"
    return "\n".join(history[-4:])


def build_user_prompt(
    step: int, observation, prompt_context: PromptContextModel, history: List[str]
) -> str:
    goal = observation.goal or "(not provided)"
    error_note = "Yes" if observation.last_action_error else "No"

    context_text = textwrap.dedent(f"""
        task: {prompt_context.task}
        assignment title: {prompt_context.assignment_title}
        deadline: {prompt_context.deadline}
        associated lecture link: {prompt_context.associated_lecture_link}
        additional task: {prompt_context.additional_task}
        Make sure all the elements in the 'details' section of given notification schema and notification instance are present.
        Labels should be string and should not contain any link.
        Convert deadline in hh:mm AM/PM format.
        Convert the given instance in to valid JSON format that can be parsed programmatically.
        Reply with exactly one EduPilot action json which adhers by given notification schema and notification instance.
        """).strip()

    prompt = textwrap.dedent(f"""
        Step: {step}
        Goal: {goal}
        Notification schema: {notification_schema}
        Example instance: {notification_instance}
        Previous steps:
        {build_history_lines(history)}
        Last action error: {error_note}
        Current context: {context_text}
        Convert the given instance in to valid JSON format that can be parsed programmatically. 
        Reply with exactly one EduPilot action json which adhers by given notification schema and notification instance.
        """).strip()

    return prompt


def parse_model_action(response_text: str) -> str:
    if not response_text:
        return FALLBACK_ACTION

    try:
        default_response_text_formatted = response_text.replace("'", '"').replace("'", '"')
        default_response_text_json = json.loads(default_response_text_formatted)
        if default_response_text_json and isinstance(default_response_text_json, dict):
            print("Default JSON conversion of model response is successful.")
            return str(default_response_text_json).replace("'", '"')
    except json.JSONDecodeError:
        print("""Default JSON conversion of model response failed. Initiated formatted parsing.....""")
        pass

    formatted_response_text_json = {}
    start_idx = response_text.find('{', 0)
    end_idx = len(response_text) - response_text[::-1].find('}', 0)
    matching_substring = response_text[start_idx:end_idx]
    formatted_substring = json.dumps(matching_substring.replace('\n', '').replace('  ',  '').replace("'", '"'))
    try:
        formatted_response_text_json = json.loads(formatted_substring)
        if formatted_response_text_json and isinstance(formatted_response_text_json, dict):
            print("Formatted JSON conversion of model response is successful.")
            return str(formatted_response_text_json).replace("'", '"')
    except:
        print("Default JSON conversion of model response failed. Initiated AI assisted parsing.....")
        formatted_response_text_json = formatted_substring

    user_prompt = [{"type": "text", 
                    "text": f"Convert the given instance in to valid JSON format that can be parsed programmatically. instance is - {formatted_response_text_json}"}]

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": JSON_PARSER_SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    inference_request_response = call_openai_inference(client=client,
                                        model_name=MODEL_NAME,
                                        prompt_messages=messages,
                                        temperature=TEMPERATURE,
                                        max_tokens=MAX_TOKENS)

    try:
        openai_response_text_json = json.loads(inference_request_response)
        if openai_response_text_json and isinstance(openai_response_text_json, dict):
            print("AI assisted parsing of model response is successful.")
            return str(openai_response_text_json).replace("'", '"')
    except json.JSONDecodeError:
        print("All parsing efforts for input request text is failed. Fallback action will be returned.")
        pass

    return FALLBACK_ACTION


async def main() -> None:
    """
    Main inference functions.
    """
    # env = await EdupilotEnv.from_env("man1103-edupilot-openenv-docker", message_timeout_s=300)
    env = await EdupilotEnv.from_docker_image(
        image=LOCAL_IMAGE_NAME,
        env_vars={
            "BRAND_NAME": "Scaler School",
            "LMS_LINK": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/",
            "ENABLE_WEB_INTERFACE": "true",
            "API_BASE_URL": "https://api.openai.com/v1",
            "MODEL_NAME": "gpt-5.4-mini",
            "LOCAL_IMAGE_NAME": "mithilesh1103/openenv-edupilot-mithilesh:latest",
            "EDUPILOT_TASK_NAME": "EduPilot Notification Generation",
            "BRAND_NAME": "Scaler School",
            "STATIC_MESSAGE_TEXT": "A new assignment has been released for you.",
            "LMS_DOMAIN_URL": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon",
            "YOUTUBE_DOMAIN_URL": "https://www.youtube.com",
            "EDUPILOT_BENCHMARK": "10.5",
        },
    )

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME or "unknown")

    try:
        result = await env.reset()
        observation = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            current_prompt_context = random.choice(prompt_context_list)

            user_prompt = build_user_prompt(step, observation, current_prompt_context, history)
            user_content = [{"type": "text", "text": user_prompt}]

            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ]

            try:
                response_text = call_openai_inference(
                    client=client,
                    model_name=MODEL_NAME,
                    prompt_messages=messages,
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
            except Exception as exc:  # noqa: BLE001
                response_text = FALLBACK_ACTION
                print(exe)
                if DEBUG:
                    print(f"[DEBUG] Model request failed: {exc}", flush=True)

            print(f"response_text: {response_text}")
            action_str = parse_model_action(response_text)
            result = await env.step(EdupilotAction(message=action_str))
            observation = result.observation

            reward = result.reward or 0.0
            error = observation.last_action_error or None
            done = result.done

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step, action=action_str, reward=reward, done=done, error=error
            )

            history_line = f"Step {step}: {action_str} -> reward {reward:+.2f}"
            if error:
                history_line += f" ERROR"
            history.append(history_line)

            if done:
                success = reward > 0.0
                break

        else:
            # Exhausted MAX_STEPS without done=true
            success = False

    finally:
        await env.close()
        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())
