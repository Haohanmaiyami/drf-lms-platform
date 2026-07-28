# LingLoop Speaking API — Flutter Contract

## Base URLs

Local:

```text
http://127.0.0.1:8000
```

Production:

```text
https://api.lingloop.org
```

## Authentication

Every Speaking API request requires:

```http
Authorization: Bearer ACCESS_TOKEN
```

Exception:

- the direct `PUT` request to the presigned S3 URL;
- never send the JWT token to Amazon S3.

---

# Complete flow

```text
1. POST create attempt
2. PUT raw M4A file to S3
3. POST complete-upload
4. GET attempt detail repeatedly
5. Stop polling at completed or failed
```

---

# Statuses

| Status | Meaning | Flutter action |
|---|---|---|
| `created` | Attempt exists; audio upload is expected | Upload the file to S3 |
| `uploaded` | S3 object was confirmed | Start polling detail |
| `transcribing` | Amazon Transcribe is processing audio | Continue polling |
| `analyzing` | Amazon Bedrock is creating feedback | Continue polling |
| `completed` | Transcript, metrics and feedback are ready | Stop polling and show result |
| `failed` | Processing failed | Stop polling and show `error.message` |

Terminal statuses:

```text
completed
failed
```

---

# 1. Create attempt

```http
POST /api/lessons/{lesson_id}/speaking-attempts/
```

Request:

```json
{
  "content_type": "audio/mp4",
  "file_extension": "m4a"
}
```

Supported content types:

```text
audio/mp4
audio/m4a
audio/x-m4a
```

Supported extension:

```text
m4a
```

Response — `201 Created`:

```json
{
  "id": "c71110b4-5844-4b18-ac83-4e6dfc7a8244",
  "lesson_id": "82449eb8-b329-4ad9-ba15-0a71349309b9",
  "attempt_number": 1,
  "status": "created",
  "upload": {
    "url": "https://temporary-presigned-s3-url",
    "method": "PUT",
    "headers": {
      "Content-Type": "audio/mp4"
    },
    "expires_in": 900
  }
}
```

Important:

```text
response.id = attempt UUID
```

Store it. It is used by all following attempt requests.

---

# 2. Upload the audio to S3

Use values returned inside `upload`.

```http
PUT {upload.url}
Content-Type: {upload.headers.Content-Type}
```

Body:

```text
raw M4A file bytes
```

Do not use:

```text
multipart/form-data
JSON
Authorization: Bearer ...
AWS credentials
```

Correct conceptual request:

```text
PUT presigned_url
Content-Type: audio/mp4
Body: raw file
```

Successful S3 response:

```text
HTTP 200
empty response body
```

The `Content-Type` header must exactly match the value returned by the backend.

The presigned URL is temporary. Do not store or log it permanently.

If the URL expires before upload completes, create a new attempt.

---

# 3. Confirm upload

```http
POST /api/speaking-attempts/{attempt_id}/complete-upload/
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

Body:

```json
{}
```

Response — `200 OK`:

```json
{
  "id": "c71110b4-5844-4b18-ac83-4e6dfc7a8244",
  "attempt_number": 1,
  "status": "uploaded",
  "audio": {
    "content_type": "audio/mp4",
    "size_bytes": 48192
  },
  "uploaded_at": "2026-07-27T02:30:00Z"
}
```

This endpoint is idempotent.

Calling it again after successful confirmation does not create a second processing pipeline.

---

# 4. Poll attempt detail

```http
GET /api/speaking-attempts/{attempt_id}/
Authorization: Bearer ACCESS_TOKEN
```

## Processing response

```json
{
  "id": "c71110b4-5844-4b18-ac83-4e6dfc7a8244",
  "lesson_id": "82449eb8-b329-4ad9-ba15-0a71349309b9",
  "attempt_number": 1,
  "status": "transcribing",
  "transcript": "",
  "metrics": null,
  "comparison": null,
  "feedback": null,
  "error": null,
  "created_at": "2026-07-27T02:29:40Z",
  "uploaded_at": "2026-07-27T02:30:00Z",
  "completed_at": null
}
```

## Completed response

```json
{
  "id": "c71110b4-5844-4b18-ac83-4e6dfc7a8244",
  "lesson_id": "82449eb8-b329-4ad9-ba15-0a71349309b9",
  "attempt_number": 1,
  "status": "completed",
  "transcript": "The customer entered the cafe and ordered coffee.",
  "metrics": {
    "duration_seconds": 40.0,
    "word_count": 10,
    "words_per_minute": 15.0,
    "filler_word_count": 1
  },
  "comparison": {
    "previous_attempt_number": 1,
    "duration_delta_seconds": -5.0,
    "words_per_minute_delta": 4.5,
    "filler_word_count_delta": -2
  },
  "feedback": {
    "overall_score": 84,
    "meaning_score": 90,
    "compression_score": 80,
    "clarity_score": 85,
    "grammar_score": 88,
    "vocabulary_score": 82,
    "fluency_score": 78,
    "covered_key_points": [
      "The customer orders coffee"
    ],
    "missed_key_points": [
      "The customer chooses the size"
    ],
    "unnecessary_details": [],
    "corrections": [
      {
        "original": "He order coffee",
        "corrected": "He orders coffee",
        "explanation": "Use -s with a third-person singular verb."
      }
    ],
    "short_feedback": "You communicated the main idea clearly.",
    "concise_version": "The customer orders a medium coffee.",
    "next_goal": "Retell the story in 45 seconds with no more than one filler word."
  },
  "error": null,
  "created_at": "2026-07-27T02:29:40Z",
  "uploaded_at": "2026-07-27T02:30:00Z",
  "completed_at": "2026-07-27T02:30:28Z"
}
```

## Failed response

```json
{
  "id": "c71110b4-5844-4b18-ac83-4e6dfc7a8244",
  "lesson_id": "82449eb8-b329-4ad9-ba15-0a71349309b9",
  "attempt_number": 1,
  "status": "failed",
  "transcript": "",
  "metrics": null,
  "comparison": null,
  "feedback": null,
  "error": {
    "code": "empty_transcript",
    "message": "The recording did not contain recognizable speech."
  },
  "created_at": "2026-07-27T02:29:40Z",
  "uploaded_at": "2026-07-27T02:30:00Z",
  "completed_at": null
}
```

Flutter should display `error.message`.

Do not display internal error details because the backend intentionally returns only a safe message.

---

# Polling rules

Recommended strategy:

```text
First 60 seconds:
poll every 2 seconds

After 60 seconds:
poll every 5 seconds

Maximum UI polling window:
10 minutes
```

Stop polling immediately when:

```text
status == completed
status == failed
```

After the UI timeout, do not delete the attempt. The user can reopen it from history later.

---

# Comparison fields

```text
duration_delta_seconds
```

Negative value:

```text
the new attempt is shorter
```

Positive value:

```text
the new attempt is longer
```

```text
words_per_minute_delta
```

Positive value:

```text
WPM increased
```

```text
filler_word_count_delta
```

Negative value:

```text
the learner used fewer filler words
```

For the first processed attempt:

```json
{
  "comparison": null
}
```

---

# 5. Attempt history

```http
GET /api/lessons/{lesson_id}/speaking-attempts/
Authorization: Bearer ACCESS_TOKEN
```

Optional query parameters:

```text
page
page_size
```

Defaults:

```text
page_size = 20
maximum page_size = 100
```

Response:

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "attempt-uuid-2",
      "lesson_id": "lesson-uuid",
      "attempt_number": 2,
      "status": "completed",
      "duration_seconds": 38.0,
      "words_per_minute": 110.0,
      "overall_score": 88,
      "created_at": "2026-07-27T02:40:00Z",
      "completed_at": "2026-07-27T02:40:25Z"
    },
    {
      "id": "attempt-uuid-1",
      "lesson_id": "lesson-uuid",
      "attempt_number": 1,
      "status": "completed",
      "duration_seconds": 45.0,
      "words_per_minute": 100.0,
      "overall_score": 80,
      "created_at": "2026-07-27T02:30:00Z",
      "completed_at": "2026-07-27T02:30:25Z"
    }
  ]
}
```

Only attempts belonging to the authenticated user are returned.

---

# Error handling

| HTTP status | Meaning | Flutter action |
|---|---|---|
| `400` | Invalid request or upload validation error | Show message; do not endlessly retry |
| `401` | Access token missing or expired | Refresh JWT and retry the API request |
| `404` | Lesson/attempt does not exist or belongs to another user | Stop and return to the previous screen |
| `503` | S3 is temporarily unavailable | Retry with a short delay |
| S3 `403` | Presigned URL is invalid or expired | Create a new attempt |
| S3 network error | Upload was interrupted | Retry the same URL while it is not expired |

---

# Security rules

Flutter must never receive or store:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3 bucket credentials
IAM credentials
```

Flutter receives only:

```text
temporary presigned upload URL
```

Do not place presigned URLs in:

```text
analytics
crash reports
permanent logs
screenshots
```

The S3 bucket remains private.

Users can access only their own SpeakingAttempt records.