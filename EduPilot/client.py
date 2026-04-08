# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Edupilot Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import EdupilotAction, EdupilotObservation
except:
    from models import EdupilotAction, EdupilotObservation

import asyncio


class EdupilotEnv(EnvClient[EdupilotAction, EdupilotObservation, State]):
    """
    Client for the Edupilot Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with EdupilotEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.echoed_message)
        ...
        ...     result = client.step(EdupilotAction(message="Hello!"))
        ...     print(result.observation.echoed_message)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = EdupilotEnv.from_docker_image("EduPilot-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(EdupilotAction(message="Test"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: EdupilotAction) -> Dict:
        """
        Convert EdupilotAction to JSON payload for step message.

        Args:
            action: EdupilotAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "message": action.message,
        }

    def _parse_result(self, payload: Dict) -> StepResult[EdupilotObservation]:
        """
        Parse server response into StepResult[EdupilotObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with EdupilotObservation
        """
        obs_data = payload.observation
        observation = EdupilotObservation(
            echoed_message=obs_data.get("echoed_message", ""),
            message_length=obs_data.get("message_length", 0),
            done=payload.done,
            reward=payload.reward,
            metadata=obs_data.metadata,
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )


msg = """{
  "notification": {
    "brand_name": "Scaler School",
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
        "value": "Faculty Session - Meta and Scaler OpenEnv Hackathon"
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
        "value": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/"
      },
      {
        "category": "extra-details",
        "type": "associated_lecture_link",
        "label": "associated lecture:",
        "value": "https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/dashboard?utm_source=midfunnel&utm_medium=email&utm_campaign=registration_acknowledgement"
      },
      {
        "category": "extra-details",
        "type": "youtube_lecture_link",
        "label": "Youtube link:",
        "value": "https://www.youtube.com/watch?v=kkCNMz0Ptd8&t=1703s"
      }
    ]
  }
}"""

async def run_client(client: EdupilotEnv):
    try:
        action = EdupilotAction(message=msg)
        step_payload = client._step_payload(action=action)
        print(f"\nstep_payload: {step_payload}")
        
        # Only call the public awaitable method
        step_result = await client.step(action=action)
        print(f"\nStep Result: {step_result}")

        # If the state is an awaitable property
        state = await client.state
        print(f"\nState: {state}")
        
    except asyncio.TimeoutError:
        print("The request timed out. Check if the server at :8001 is responsive.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    client = EdupilotEnv(base_url="http://localhost:8001/", message_timeout_s=200)
    asyncio.run(run_client(client=client))