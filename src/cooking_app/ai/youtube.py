import re
from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split(":")[0]

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("YouTube URL must use http or https")

    if host not in YOUTUBE_HOSTS:
        raise ValueError("URL must belong to YouTube")

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith("/shorts/"):
        video_id = parsed.path.removeprefix("/shorts/").split("/")[0]
    elif parsed.path.startswith("/embed/"):
        video_id = parsed.path.removeprefix("/embed/").split("/")[0]
    else:
        video_id = ""

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("Could not find a valid YouTube video ID")

    return video_id
