import pytest
from app.services import extract_video_id, chunk_text, estimate_time_saved

def test_extract_video_id():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    with pytest.raises(ValueError):
        extract_video_id("https://google.com")

def test_chunk_text():
    text = "word " * 1000
    chunks = chunk_text(text, max_tokens=100, overlap=10)
    assert len(chunks) > 1
    assert "word" in chunks[0]

def test_estimate_time_saved():
    # ~2000 words
    saved = estimate_time_saved(10000)
    assert saved > 0
