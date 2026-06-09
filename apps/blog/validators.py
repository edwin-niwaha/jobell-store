from urllib.parse import parse_qs, urlparse
from django.core.exceptions import ValidationError


YOUTUBE_HOSTS = {
    "www.youtube.com",
    "youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def extract_youtube_video_id(value):
    """Return a YouTube video ID from common watch, short, and embed URLs."""
    if not value:
        return ""

    parsed_url = urlparse(value.strip())
    host = parsed_url.netloc.lower()
    if host.startswith("www."):
        normalized_host = host[4:]
    else:
        normalized_host = host

    if host not in YOUTUBE_HOSTS and normalized_host not in YOUTUBE_HOSTS:
        return ""

    if normalized_host == "youtu.be":
        return parsed_url.path.strip("/").split("/")[0]

    query_video_id = parse_qs(parsed_url.query).get("v")
    if query_video_id:
        return query_video_id[0]

    path_parts = [part for part in parsed_url.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts"}:
        return path_parts[1]

    return ""


def build_youtube_embed_url(value):
    video_id = extract_youtube_video_id(value)
    if not video_id:
        return ""
    return f"https://www.youtube.com/embed/{video_id}"


def validate_youtube_url(value):
    """Validator to ensure the provided URL is a valid YouTube video link."""
    parsed_url = urlparse(value)
    host = parsed_url.netloc.lower()
    normalized_host = host[4:] if host.startswith("www.") else host

    if host not in YOUTUBE_HOSTS and normalized_host not in YOUTUBE_HOSTS:
        raise ValidationError("Please provide a valid YouTube URL.")
    if not extract_youtube_video_id(value):
        raise ValidationError("Invalid YouTube URL. Ensure it contains a video ID.")
