# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Edupilot Environment Implementation.

A simple test environment that echoes back messages sent to it.
Perfect for testing HTTP server infrastructure.
"""

from uuid import uuid4
from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import EdupilotAction, EdupilotObservation
except ImportError:
    from models import EdupilotAction, EdupilotObservation


class EdupilotEnvironment(Environment):
    """
    A simple echo environment that echoes back messages.

    This environment is designed for testing the HTTP server infrastructure.
    It maintains minimal state and simply echoes back whatever message it receives.

    Example:
        >>> env = EdupilotEnvironment()
        >>> obs = env.reset()
        >>> print(obs.echoed_message)  # "Edupilot environment ready!"
        >>>
        >>> obs = env.step(EdupilotAction(message="Hello"))
        >>> print(obs.echoed_message)  # "Hello"
        >>> print(obs.message_length)  # 5
    """

    # Enable concurrent WebSocket sessions.
    # Set to True if your environment isolates state between instances.
    # When True, multiple WebSocket clients can connect simultaneously, each
    # getting their own environment instance (when using factory mode in app.py).
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the EduPilot environment."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count = 0

    def reset(self,
            seed: Optional[int] = None,
            episode_id: Optional[str] = None,
            **kwargs: Any
            ) -> EdupilotObservation:
        """
        Reset the environment.

        Returns:
            EdupilotObservation with a ready message
        """
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count += 1

        return EdupilotObservation(
            echoed_message="Edupilot environment ready!",
            message_length=0,
            done=False,
            reward=0.0,
        )

    def parse_llm_response(self, message: str):
        parsed_msg_dict = {
            "brand_name": {
                "enclosures": False,
                "value": False
            },
            "greetings": {
                "enclosures": False,
                "value": False
            },
            "main_details": {
                "enclosures": False,
                "value": False
            },
            "extra_details": {
                "enclosures": False,
                "value": False
            }
        }

        for msg_part in message.split("<br>"):
            if "<brand name>" and "</brand name>" in msg_part:
                parsed_msg_dict["brand_name"]["enclosures"] = True
                if "Masai School" in msg_part:
                    parsed_msg_dict["brand_name"]["value"] = True
            elif "<greetings>" and "</greetings>" in msg_part:
                parsed_msg_dict["greetings"]["enclosures"] = True
                if "Dear " in msg_part:
                    parsed_msg_dict["greetings"]["value"] = True
            elif "<main-details>" and "</main-details>" in msg_part:
                parsed_msg_dict["main_details"]["enclosures"] = True
                if ("📘 Assignment Title: " in msg_part and "🗓 Deadline: " in msg_part and "🔗 LMS Link: " in msg_part):
                    parsed_msg_dict["main_details"]["value"] = True
            elif "<extra-details>" and "</extra-details>" in msg_part:
                parsed_msg_dict["extra_details"]["enclosures"] = True
                if ("associated lecture: " in msg_part and "Youtube link: " in msg_part):
                    parsed_msg_dict["extra_details"]["value"] = True

        print(f"parsed_msg_dict: {parsed_msg_dict}")
        return parsed_msg_dict

    def reward_collection(self, parsed_msg_dict: dict):
        rewards_collected = []
        observations = []
        parsed_elements = ["brand_name", "greetings", "main_details", "extra_details"]

        for key in parsed_elements:
            if parsed_msg_dict[key]["enclosures"]:
                enclosure_reward = 5
                rewards_collected.append(enclosure_reward)
                observations.append(f"Element '{key}_enclosures' found in message, therefore reward of {enclosure_reward} was given.")
            else:
                default_reward = 0.5
                rewards_collected.append(default_reward)
                observations.append(f"Required '{key}_enclosures' was not found in message, therefore default reward of {default_reward} was given.")

            if parsed_msg_dict[key]["value"]:
                value_reward = 10
                rewards_collected.append(value_reward)
                observations.append(f"Element '{key}_value' found in message, therefore reward of {value_reward} was given.")
            else:
                default_reward = 0.5
                rewards_collected.append(default_reward)
                observations.append(f"Required '{key}_value' was not found in message, therefore default reward of {default_reward} was given.")

        return rewards_collected, observations

    def step(self, action: EdupilotAction) -> EdupilotObservation:  # type: ignore[override]
        """
        Execute a step in the environment by echoing the message.

        Args:
            action: EdupilotAction containing the message to echo

        Returns:
            EdupilotObservation with the echoed message and its length
        """
        self._state.step_count += 1

        message = action.message
        length = len(message)

        # Simple reward: longer messages get higher rewards
        # reward = length * 0.1
        parsed_msg_dict = self.parse_llm_response(message)
        rewards_collected, observations = self.reward_collection(parsed_msg_dict)

        final_reward = sum(rewards_collected)

        return EdupilotObservation(
            echoed_message=message,
            message_length=length,
            reward_observations=observations,
            done=False,
            reward=final_reward,
            metadata={"original_message": message, "step": self._state.step_count},
        )

    @property
    def state(self) -> State:
        """
        Get the current environment state.

        Returns:
            Current State with episode_id and step_count
        """
        return self._state
