from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


SCORE_FIELDS = (
    "overall_score",
    "meaning_score",
    "compression_score",
    "clarity_score",
    "grammar_score",
    "vocabulary_score",
    "fluency_score",
)

LIST_FIELDS = (
    "covered_key_points",
    "missed_key_points",
    "unnecessary_details",
)

TEXT_FIELDS = (
    "short_feedback",
    "concise_version",
    "next_goal",
)


class CorrectionItem(BaseModel):
    """Одно конкретное языковое исправление."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    original: str
    corrected: str
    explanation: str

    @field_validator(
        "original",
        "corrected",
        "explanation",
    )
    @classmethod
    def validate_non_empty_text(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Correction text must not be empty."
            )

        return value


class SpeakingFeedbackPayload(BaseModel):
    """Проверенный ответ Amazon Bedrock."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    overall_score: int = Field(
        ge=0,
        le=100,
    )
    meaning_score: int = Field(
        ge=0,
        le=100,
    )
    compression_score: int = Field(
        ge=0,
        le=100,
    )
    clarity_score: int = Field(
        ge=0,
        le=100,
    )
    grammar_score: int = Field(
        ge=0,
        le=100,
    )
    vocabulary_score: int = Field(
        ge=0,
        le=100,
    )
    fluency_score: int = Field(
        ge=0,
        le=100,
    )

    covered_key_points: list[str]
    missed_key_points: list[str]
    unnecessary_details: list[str]

    corrections: list[
        CorrectionItem
    ] = Field(
        max_length=5,
    )

    short_feedback: str
    concise_version: str
    next_goal: str

    @field_validator(
        *LIST_FIELDS,
    )
    @classmethod
    def normalize_string_lists(
        cls,
        value: list[str],
    ) -> list[str]:
        return [
            item.strip()
            for item in value
            if item.strip()
        ]

    @field_validator(
        *TEXT_FIELDS,
    )
    @classmethod
    def validate_feedback_text(
        cls,
        value: str,
    ) -> str:
        if not value:
            raise ValueError(
                "Feedback text must not be empty."
            )

        return value

    def to_model_defaults(self) -> dict:
        """
        Подготавливает данные для SpeakingFeedback.

        Итоговый overall рассчитываем
        из компонентных AI-оценок.
        """

        data = self.model_dump()

        data["overall_score"] = round(
            self.meaning_score * 0.30
            + self.compression_score * 0.15
            + self.clarity_score * 0.15
            + self.grammar_score * 0.10
            + self.vocabulary_score * 0.10
            + self.fluency_score * 0.20
        )

        return data


BEDROCK_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {
            "type": "integer",
            "description": (
                "Overall speaking score "
                "from 0 to 100."
            ),
        },
        "meaning_score": {
            "type": "integer",
            "description": (
                "Meaning coverage score "
                "from 0 to 100."
            ),
        },
        "compression_score": {
            "type": "integer",
            "description": (
                "Conciseness score "
                "from 0 to 100."
            ),
        },
        "clarity_score": {
            "type": "integer",
            "description": (
                "Clarity score "
                "from 0 to 100."
            ),
        },
        "grammar_score": {
            "type": "integer",
            "description": (
                "Grammar score "
                "from 0 to 100."
            ),
        },
        "vocabulary_score": {
            "type": "integer",
            "description": (
                "Vocabulary score "
                "from 0 to 100."
            ),
        },
        "fluency_score": {
            "type": "integer",
            "description": (
                "Fluency score "
                "from 0 to 100."
            ),
        },
        "covered_key_points": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "missed_key_points": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "unnecessary_details": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {
                        "type": "string",
                    },
                    "corrected": {
                        "type": "string",
                    },
                    "explanation": {
                        "type": "string",
                    },
                },
                "required": [
                    "original",
                    "corrected",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        },
        "short_feedback": {
            "type": "string",
        },
        "concise_version": {
            "type": "string",
        },
        "next_goal": {
            "type": "string",
        },
    },
    "required": [
        *SCORE_FIELDS,
        *LIST_FIELDS,
        "corrections",
        *TEXT_FIELDS,
    ],
    "additionalProperties": False,
}