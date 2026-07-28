#!/usr/bin/env bash

set -euo pipefail


: "${BASE_URL:?Set BASE_URL}"
: "${ACCESS_TOKEN:?Set ACCESS_TOKEN}"
: "${LESSON_ID:?Set LESSON_ID}"
: "${AUDIO_FILE:?Set AUDIO_FILE}"


CONTENT_TYPE="${CONTENT_TYPE:-audio/mp4}"
FILE_EXTENSION="${FILE_EXTENSION:-m4a}"
POLL_SECONDS="${POLL_SECONDS:-2}"
MAX_POLLS="${MAX_POLLS:-300}"

BASE_URL="${BASE_URL%/}"


if [[ ! -f "${AUDIO_FILE}" ]]; then
    echo "Audio file not found: ${AUDIO_FILE}" >&2
    exit 1
fi


echo "1. Creating speaking attempt..."

CREATE_RESPONSE="$(
    curl \
        --silent \
        --show-error \
        --fail-with-body \
        --request POST \
        "${BASE_URL}/api/lessons/${LESSON_ID}/speaking-attempts/" \
        --header "Authorization: Bearer ${ACCESS_TOKEN}" \
        --header "Content-Type: application/json" \
        --data "{
            \"content_type\": \"${CONTENT_TYPE}\",
            \"file_extension\": \"${FILE_EXTENSION}\"
        }"
)"


ATTEMPT_ID="$(
    printf '%s' "${CREATE_RESPONSE}" |
        python -c '
import json
import sys

payload = json.load(sys.stdin)
print(payload["id"])
'
)"


UPLOAD_URL="$(
    printf '%s' "${CREATE_RESPONSE}" |
        python -c '
import json
import sys

payload = json.load(sys.stdin)
print(payload["upload"]["url"])
'
)"


UPLOAD_CONTENT_TYPE="$(
    printf '%s' "${CREATE_RESPONSE}" |
        python -c '
import json
import sys

payload = json.load(sys.stdin)
print(
    payload["upload"]["headers"][
        "Content-Type"
    ]
)
'
)"


echo "Attempt ID: ${ATTEMPT_ID}"
echo "2. Uploading raw audio directly to S3..."


curl \
    --silent \
    --show-error \
    --fail-with-body \
    --request PUT \
    "${UPLOAD_URL}" \
    --header "Content-Type: ${UPLOAD_CONTENT_TYPE}" \
    --upload-file "${AUDIO_FILE}" \
    --output /dev/null


echo "S3 upload completed."
echo "3. Confirming upload with backend..."


COMPLETE_RESPONSE="$(
    curl \
        --silent \
        --show-error \
        --fail-with-body \
        --request POST \
        "${BASE_URL}/api/speaking-attempts/${ATTEMPT_ID}/complete-upload/" \
        --header "Authorization: Bearer ${ACCESS_TOKEN}" \
        --header "Content-Type: application/json" \
        --data '{}'
)"


printf '%s\n' "${COMPLETE_RESPONSE}" |
    python -m json.tool


echo "4. Polling attempt detail..."


for ((poll=1; poll<=MAX_POLLS; poll++)); do
    DETAIL_RESPONSE="$(
        curl \
            --silent \
            --show-error \
            --fail-with-body \
            "${BASE_URL}/api/speaking-attempts/${ATTEMPT_ID}/" \
            --header "Authorization: Bearer ${ACCESS_TOKEN}"
    )"

    ATTEMPT_STATUS="$(
        printf '%s' "${DETAIL_RESPONSE}" |
            python -c '
import json
import sys

payload = json.load(sys.stdin)
print(payload["status"])
'
    )"

    echo "Poll ${poll}/${MAX_POLLS}: ${ATTEMPT_STATUS}"

    case "${ATTEMPT_STATUS}" in
        completed)
            echo "Speaking attempt completed."
            printf '%s\n' "${DETAIL_RESPONSE}" |
                python -m json.tool
            exit 0
            ;;

        failed)
            echo "Speaking attempt failed." >&2
            printf '%s\n' "${DETAIL_RESPONSE}" |
                python -m json.tool
            exit 1
            ;;
    esac

    sleep "${POLL_SECONDS}"
done


echo "Polling timed out." >&2
echo "Attempt remains available: ${ATTEMPT_ID}" >&2
exit 1