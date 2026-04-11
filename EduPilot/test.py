try:
    from ..models import EdupilotAction, EdupilotObservation
    from .client import EdupilotEnv
except ImportError:
    from models import EdupilotAction, EdupilotObservation
    from client import EdupilotEnv

import asyncio


async def fetch_env():
    env = await EdupilotEnv.from_env(
        "man1103/edupilot-openenv-docker",
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
    
    return env


async def main_test():
    env = await fetch_env()
    result = await env.reset()
    print(result)


if __name__ == "__main__":
    asyncio.run(main_test())
