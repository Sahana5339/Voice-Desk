import struct

import pytest

import syst


class R:
    def __init__(self, status, content=b"RIFF....data...."):
        self.status_code, self.content, self.text = status, content, "err"


def test_fix_wav_patches_unknown_length_header():
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(48000), w.writeframes(b"\x00\x01" * 4800)
    bad = bytearray(buf.getvalue())
    struct.pack_into("<I", bad, 4, 0xFFFFFFFF)
    j = bytes(bad).find(b"data")
    struct.pack_into("<I", bad, j + 4, 0xFFFFFFFF)
    with wave.open(io.BytesIO(syst.fix_wav(bytes(bad)))) as w:
        assert w.getnframes() == 4800


def test_tts_prefers_v3_then_falls_back_to_v2_5_and_remembers(monkeypatch):
    monkeypatch.delenv("TIMBRE_MODEL", raising=False)
    syst._tts_choice["idx"] = None
    calls = []

    def fake(text, model, voice, lang, key, speed=1.0):
        calls.append(model)
        return R(400) if model == "timbre-v3.0" else R(200)
    monkeypatch.setattr(syst, "_tts_request", fake)
    syst.synthesize("hello", "en", "k")
    syst.synthesize("hello", "en", "k")
    assert calls == ["timbre-v3.0", "timbre-v2.5", "timbre-v2.5"]  # v3.0 not retried after it failed once


def test_tts_uses_v3_when_it_works(monkeypatch):
    monkeypatch.delenv("TIMBRE_MODEL", raising=False)
    syst._tts_choice["idx"] = None
    used = []
    monkeypatch.setattr(syst, "_tts_request", lambda t, m, v, l, k, speed=1.0: used.append(m) or R(200))
    syst.synthesize("hi", "hi", "k")
    assert used == ["timbre-v3.0"]


def test_validate_gnani_api_key_rejects_placeholder_values(monkeypatch):
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        syst.validate_gnani_api_key()

    monkeypatch.setenv("GNANI_API_KEY", "your_gnani_key_here")
    with pytest.raises(RuntimeError):
        syst.validate_gnani_api_key()

    monkeypatch.setenv("GNANI_API_KEY", "real-key-12345")
    assert syst.validate_gnani_api_key() == "real-key-12345"
