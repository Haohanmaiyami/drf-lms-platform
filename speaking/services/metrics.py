import re
from dataclasses import dataclass


WORD_PATTERN = re.compile(
    r"[A-Za-z]+(?:'[A-Za-z]+)?"
)

FILLER_PATTERNS = (
    re.compile(
        r"\bu+m+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bu+h+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\ber+m+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bh+m+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou know\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi mean\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class SpeechMetrics:
    duration_seconds: float
    word_count: int
    words_per_minute: float
    filler_word_count: int


def count_filler_words(
    transcript: str,
) -> int:
    return sum(
        len(pattern.findall(transcript))
        for pattern in FILLER_PATTERNS
    )


def calculate_speech_metrics(
    *,
    transcript: str,
    duration_seconds: float,
) -> SpeechMetrics:
    cleaned_transcript = transcript.strip()

    rounded_duration = round(
        float(duration_seconds),
        2,
    )

    if not cleaned_transcript:
        raise ValueError(
            "Transcript is empty."
        )

    if rounded_duration <= 0:
        raise ValueError(
            "Audio duration must be positive."
        )

    words = WORD_PATTERN.findall(
        cleaned_transcript
    )

    if not words:
        raise ValueError(
            "Transcript contains no words."
        )

    word_count = len(words)

    words_per_minute = round(
        word_count * 60 / rounded_duration,
        2,
    )

    return SpeechMetrics(
        duration_seconds=rounded_duration,
        word_count=word_count,
        words_per_minute=words_per_minute,
        filler_word_count=(
            count_filler_words(
                cleaned_transcript
            )
        ),
    )