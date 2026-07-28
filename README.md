# LingLoop Backend

Backend API for LingLoop — a speaking-fluency application built around:

```text
Watch → Retell → Improve
```

A learner watches a short lesson, records a retelling, receives a transcript, speech metrics and structured AI feedback, then records another attempt and compares progress.

---

## MVP access rules

- All authenticated users can access lessons
- Course subscription is not required
- Speaking is enabled when a lesson has `LessonSpeakingConfig`
- Users can access only their own speaking attempts

---

## Speaking pipeline

```text
created
→ uploaded
→ transcribing
→ analyzing
→ completed
```

Error status:

```text
failed
```

Processing flow:

```text
Flutter
→ Django REST API
→ direct upload to private Amazon S3
→ Celery
→ Amazon Transcribe
→ Python speech metrics
→ Amazon Bedrock
→ structured SpeakingFeedback
```

---

## Main technologies

- Python 3.13
- Django 5
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Docker Compose
- Amazon S3
- Amazon Transcribe
- Amazon Bedrock
- Pydantic
- JWT authentication
- drf-yasg / Swagger

---

## Speaking API

```http
POST /api/lessons/{lesson_id}/speaking-attempts/
POST /api/speaking-attempts/{attempt_id}/complete-upload/
GET  /api/speaking-attempts/{attempt_id}/
GET  /api/lessons/{lesson_id}/speaking-attempts/
```

Flutter integration contract:

```text
docs/flutter-speaking-api.md
```

Swagger:

```text
http://127.0.0.1:8000/swagger/
```

Production Swagger:

```text
https://api.lingloop.org/swagger/
```

---

## Local setup

Create `.env` from the example:

```bash
cp .env.example .env
```

Add the required PostgreSQL, Redis and AWS values.

Build and start:

```bash
docker compose build
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Apply migrations:

```bash
docker compose exec web python manage.py migrate
```

---

## Checks

```bash
docker compose exec web python manage.py check
```

```bash
docker compose exec web python manage.py makemigrations --check
```

Run the test suite:

```bash
docker compose exec web pytest speaking/tests courses/tests.py
```

---

## Celery

Registered tasks include:

```text
speaking.tasks.process_speaking_attempt
speaking.tasks.poll_speaking_transcription
speaking.tasks.analyze_speaking_attempt
```

Inspect registered tasks:

```bash
docker compose exec celery \
  celery -A config inspect registered
```

Follow worker logs:

```bash
docker compose logs -f celery
```

---

## End-to-end test

Required environment variables:

```text
BASE_URL
ACCESS_TOKEN
LESSON_ID
AUDIO_FILE
```

Example:

```bash
BASE_URL=http://127.0.0.1:8000 \
ACCESS_TOKEN="JWT_ACCESS_TOKEN" \
LESSON_ID="LESSON_UUID" \
AUDIO_FILE="$HOME/Downloads/sample.m4a" \
./scripts/speaking_e2e.sh
```

---

## Security

Never commit:

```text
.env
AWS credentials
presigned URLs
user audio
transcription output
```

The S3 bucket must remain private.

Flutter receives only a temporary presigned URL and never receives AWS credentials.

---

## Project structure

```text
courses/
speaking/
    services/
        attempts.py
        storage.py
        uploads.py
        transcription.py
        metrics.py
        feedback_prompt.py
        feedback_schema.py
        bedrock.py
    tests/
    tasks.py
users/
config/
docs/
scripts/
deploy/
```