from pathlib import Path
import pytest
from app.birdnet_service import analyze_audio


def test_missing_or_empty_audio():
    res = analyze_audio("non_existent_file.wav")
    assert res["success"] is False
    assert res["identified"] is False
    assert "empty or missing" in res["message"]


def test_low_confidence_graceful_failure():
    sample_file = Path("samples/sample_bird.wav")
    assert sample_file.exists(), "Sample file must exist for tests"

    # With high threshold (e.g. 0.8), our synthetic chirp must be rejected gracefully
    res = analyze_audio(str(sample_file), confidence_threshold=0.80)
    assert res["success"] is True
    assert res["identified"] is False
    assert "Couldn't tell, try again" in res["message"]
    assert res["top_species"] is None


def test_low_threshold_detection():
    sample_file = Path("samples/sample_bird.wav")
    assert sample_file.exists()

    # With very low threshold (0.1), detection succeeds
    res = analyze_audio(str(sample_file), confidence_threshold=0.10)
    assert res["success"] is True
    assert res["identified"] is True
    assert res["top_species"] is not None
    assert "common_name" in res["top_species"]
    assert "confidence" in res["top_species"]
    assert res["top_species"]["confidence"] >= 0.10
