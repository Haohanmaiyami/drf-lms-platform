from urllib.parse import urlparse
from rest_framework import serializers

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


def validate_youtube_url(value):
    """
    Разрешаем только youtube-ссылки в поле video (или пустое значение).
    """
    if value in (None, ""):
        return value
    try:
        host = urlparse(value).netloc.lower()
    except Exception:
        raise serializers.ValidationError("Некорректная ссылка.")
    if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        raise serializers.ValidationError("Разрешены только ссылки на YouTube.")
    return value
