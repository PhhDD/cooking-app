import os
from dataclasses import dataclass
from typing import Any

import httpx

from cooking_app.ai.youtube import extract_video_id


class YouTubeMetadataError(RuntimeError):
    """Raised when YouTube metadata cannot be retrieved."""


@dataclass(frozen=True)
class YouTubeVideoMetadata:
    video_id: str
    title: str
    description: str
    channel_title: str
    published_at: str
    source_url: str


def fetch_video_metadata(
    video_url: str,
    client: httpx.Client | None = None,
) -> YouTubeVideoMetadata:
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        raise YouTubeMetadataError("YOUTUBE_API_KEY is not configured")

    video_id = extract_video_id(video_url)
    owns_client = client is None
    request_client = client or httpx.Client(timeout=10.0)

    try:
        response = request_client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet",
                "id": video_id,
                "key": api_key,
            },
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise YouTubeMetadataError(
            "YouTube metadata request failed",
        ) from error
    finally:
        if owns_client:
            request_client.close()

    payload: dict[str, Any] = response.json()
    items = payload.get("items", [])

    if not items:
        raise YouTubeMetadataError("YouTube video was not found")

    snippet = items[0]["snippet"]

    return YouTubeVideoMetadata(
        video_id=video_id,
        title=snippet.get("title", "").strip(),
        description=snippet.get("description", "").strip(),
        channel_title=snippet.get("channelTitle", "").strip(),
        published_at=snippet.get("publishedAt", ""),
        source_url=f"https://www.youtube.com/watch?v={video_id}",
    )
