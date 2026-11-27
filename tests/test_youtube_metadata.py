import httpx
import pytest

from cooking_app.ai.youtube_metadata import (
    YouTubeMetadataError,
    fetch_video_metadata,
)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.url = None
        self.params = None

    def get(self, url, params):
        self.url = url
        self.params = params
        return self.response


def test_fetch_video_metadata(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")

    response = httpx.Response(
        200,
        request=httpx.Request(
            "GET",
            "https://www.googleapis.com/youtube/v3/videos",
        ),
        json={
            "items": [
                {
                    "snippet": {
                        "title": "Test Recipe",
                        "description": "Recipe description",
                        "channelTitle": "Test Channel",
                        "publishedAt": "2026-01-01T00:00:00Z",
                    }
                }
            ]
        },
    )
    client = FakeClient(response)

    metadata = fetch_video_metadata(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        client=client,
    )

    assert metadata.video_id == "dQw4w9WgXcQ"
    assert metadata.title == "Test Recipe"
    assert metadata.description == "Recipe description"
    assert metadata.channel_title == "Test Channel"
    assert metadata.source_url == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    assert client.params["key"] == "test-key"


def test_fetch_video_metadata_requires_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    with pytest.raises(
        YouTubeMetadataError,
        match="YOUTUBE_API_KEY is not configured",
    ):
        fetch_video_metadata(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )


def test_fetch_video_metadata_rejects_missing_video(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")

    response = httpx.Response(
            200,
            request=httpx.Request(
                "GET",
                "https://www.googleapis.com/youtube/v3/videos",
            ),
            json={"items": []},
    )
    client = FakeClient(response)

    with pytest.raises(
        YouTubeMetadataError,
        match="YouTube video was not found",
    ):
        fetch_video_metadata(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            client=client,
        )
