import pytest

import voice_service


def test_transcribe_routes_language_and_filename(monkeypatch):
    calls = []

    def fake_transcribe(audio, language, model, filename):
        calls.append((audio, language, model, filename))
        return {"text": "hello", "lang": language, "model": model, "stt_ms": 1}

    monkeypatch.setattr(voice_service.syst, "transcribe", fake_transcribe)
    result, notes = voice_service.transcribe(b"audio", "Hindi", "complaint.wav")

    assert result["text"] == "hello"
    assert notes == []
    assert calls == [(b"audio", "hi-IN", None, "complaint.wav")]


def test_auto_detect_retries_in_hindi_and_returns_note(monkeypatch):
    calls = []

    def fake_transcribe(audio, language, model, filename):
        calls.append(language)
        if language == "indic-auto":
            raise RuntimeError("auto unavailable")
        return {"text": "नमस्ते", "lang": language, "model": model, "stt_ms": 1}

    monkeypatch.setattr(voice_service.syst, "transcribe", fake_transcribe)
    result, notes = voice_service.transcribe(b"audio", "Auto-detect (Prisma v3.0)")

    assert result["lang"] == "hi-IN"
    assert calls == ["indic-auto", "hi-IN"]
    assert len(notes) == 1 and "retried as Hindi" in notes[0]


def test_fixed_language_transcription_error_is_not_retried(monkeypatch):
    calls = []

    def fail(audio, language, model, filename):
        calls.append(language)
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(voice_service.syst, "transcribe", fail)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        voice_service.transcribe(b"audio", "Kannada")
    assert calls == ["kn-IN"]
