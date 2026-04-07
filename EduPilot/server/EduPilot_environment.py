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
import json
import jsonschema
from jsonschema import Draft7Validator

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import EdupilotAction, EdupilotObservation
except ImportError:
    from models import EdupilotAction, EdupilotObservation

try:
    from .reward_collection import parse_llm_response, reward_collection
except ImportError:
    from server.reward_collection import parse_llm_response, reward_collection


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

        message = json.loads(message)
        print(message)
        
        message_schema = {}
        message_schema_file_path = r"EduPilot\validation_schema.json"
        with open(message_schema_file_path, "r+") as file:
            message_schema = json.load(file)
            # print(message_schema)

        final_reward = 0
        observations = [{"Exception": "Input message json schema validation failed. Therefore no rewards given."}]
        if isinstance(message, dict):
            try:
                validator = Draft7Validator(message_schema)
                validation_result = validator.validate(message)
                if validation_result==None:
                    parsed_dict = parse_llm_response(message)
                    rewards_collected, observations = reward_collection(parsed_dict)
                    final_reward = sum(rewards_collected)
            except jsonschema.exceptions.ValidationError:
                print("Schema validation failed.")

        return EdupilotObservation(
            echoed_message=json.dumps(message),
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
