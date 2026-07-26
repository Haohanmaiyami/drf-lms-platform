import logging
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from django.conf import settings
from pydantic import ValidationError

from speaking.services.feedback_prompt import (
    SYSTEM_PROMPT,
    build_feedback_prompt,
)
from speaking.services.feedback_schema import (
    BEDROCK_FEEDBACK_SCHEMA,
    SpeakingFeedbackPayload,
)


logger = logging.getLogger(__name__)

FEEDBACK_TOOL_NAME = (
    "submit_speaking_feedback"
)


class BedrockServiceError(Exception):
    """Amazon Bedrock временно недоступен."""


class BedrockInvalidResponse(Exception):
    """
    Модель вернула ответ,
    не прошедший проверку.
    """


@lru_cache(maxsize=1)
def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.AWS_REGION,
        config=Config(
            connect_timeout=10,
            read_timeout=120,
            retries={
                "max_attempts": 3,
                "mode": "standard",
            },
        ),
    )


def build_feedback_tool_config() -> dict:
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": (
                        FEEDBACK_TOOL_NAME
                    ),
                    "description": (
                        "Submit the complete "
                        "structured LingLoop "
                        "speaking feedback."
                    ),
                    "inputSchema": {
                        "json": (
                            BEDROCK_FEEDBACK_SCHEMA
                        )
                    },
                }
            }
        ],
        "toolChoice": {
            "tool": {
                "name": (
                    FEEDBACK_TOOL_NAME
                ),
            }
        },
    }


def extract_feedback_input(
    response: dict,
) -> dict:
    content = (
        response
        .get("output", {})
        .get("message", {})
        .get("content", [])
    )

    for block in content:
        tool_use = block.get(
            "toolUse"
        )

        if not tool_use:
            continue

        if (
            tool_use.get("name")
            != FEEDBACK_TOOL_NAME
        ):
            continue

        tool_input = tool_use.get(
            "input"
        )

        if not isinstance(
            tool_input,
            dict,
        ):
            break

        return tool_input

    raise BedrockInvalidResponse(
        "Bedrock did not return "
        "the required feedback tool input."
    )


def request_feedback(
    *,
    prompt: str,
) -> dict:
    try:
        return (
            get_bedrock_client()
            .converse(
                modelId=(
                    settings
                    .AWS_BEDROCK_MODEL_ID
                ),
                system=[
                    {
                        "text": (
                            SYSTEM_PROMPT
                        ),
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": (
                        settings
                        .AWS_BEDROCK_MAX_TOKENS
                    ),
                    "temperature": (
                        settings
                        .AWS_BEDROCK_TEMPERATURE
                    ),
                },
                toolConfig=(
                    build_feedback_tool_config()
                ),
            )
        )

    except (
        BotoCoreError,
        ClientError,
    ) as exc:
        raise BedrockServiceError(
            "Could not generate "
            "speaking feedback."
        ) from exc


def generate_speaking_feedback(
    *,
    attempt,
) -> SpeakingFeedbackPayload:
    base_prompt = build_feedback_prompt(
        attempt
    )

    validation_retries = (
        settings
        .AWS_BEDROCK_VALIDATION_RETRIES
    )

    last_error = None

    for validation_attempt in range(
        validation_retries + 1
    ):
        prompt = base_prompt

        if validation_attempt > 0:
            prompt += (
                "\n\nYour previous result failed "
                "backend validation. Return every "
                "required field, use scores only "
                "from 0 to 100, do not use blank "
                "strings, and call the required "
                "tool once."
            )

        response = request_feedback(
            prompt=prompt,
        )

        try:
            tool_input = (
                extract_feedback_input(
                    response
                )
            )

            return (
                SpeakingFeedbackPayload
                .model_validate(
                    tool_input
                )
            )

        except (
            BedrockInvalidResponse,
            ValidationError,
        ) as exc:
            last_error = exc

            logger.warning(
                "Invalid Bedrock feedback "
                "response. Validation attempt "
                "%s of %s.",
                validation_attempt + 1,
                validation_retries + 1,
            )

    raise BedrockInvalidResponse(
        "Bedrock feedback "
        "failed validation."
    ) from last_error