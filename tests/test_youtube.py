import pytest

from cooking_app.ai.youtube import extract_video_id


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "not-a-url",
        "https://www.youtube.com/watch?v=too-short",
    ],
)
def test_extract_video_id_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        extract_video_id(url)
