"""Gnani AI API helpers: Prisma v3.0 speech-to-text and Timbre (v3.0 with v2.5 fallback) text-to-speech (REST)."""
import os
import struct
import time

import requests

import settings

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

# label -> (language_code, model or None for the default Prisma v2.5)
LANGS = {
    "Auto-detect (Prisma v3.0)": ("indic-auto", "prisma-v3.0"),
    "Hindi": ("hi-IN", None), "Kannada": ("kn-IN", None), "English (India)": ("en-IN", None),
    "Tamil": ("ta-IN", None), "Telugu": ("te-IN", None), "Marathi": ("mr-IN", None),
    "Bengali": ("bn-IN", None), "Malayalam": ("ml-IN", None), "Gujarati": ("gu-IN", None),
    "Punjabi": ("pa-IN", None),
}
# Timbre voices. v2.5 voices each have one preferred language (verified earlier in this project).
VOICES_V25 = {"hi": ("Chitra", "hi-IN"), "en": ("Kaveri", "en-IN"), "kn": ("Kavin", "kn-IN")}
# Timbre v3.0 voice 'Kalpana' is reported as multilingual but is not yet verified here.
# Run `python probe_tts.py` once with your key; synthesize() also falls back to v2.5 automatically if v3.0 fails.
VOICES_V30 = {"hi": ("Kalpana", "hi-IN"), "en": ("Kalpana", "en-IN"), "kn": ("Kalpana", "kn-IN")}
TTS_MODELS = [("timbre-v3.0", VOICES_V30), ("timbre-v2.5", VOICES_V25)]  # preferred first
VOICES = VOICES_V25  # kept for backwards compatibility
_tts_choice = {"idx": None}  # remembers which model worked, so a failed v3.0 is not retried on every call

def validate_gnani_api_key(api_key=None):
    """Compatibility wrapper for callers that validate Gnani credentials."""
    return settings.gnani_api_key(api_key)


def transcribe(audio_bytes, language_code="indic-auto", model="prisma-v3.0", api_key=None, filename="audio.wav"):
    """Returns {'text', 'lang', 'model', 'stt_ms'}. Raises on HTTP/API errors."""
    api_key = validate_gnani_api_key(api_key)
    data = {"language_code": language_code}
    if model:
        data["model"] = model
    t0 = time.time()
    r = requests.post(STT_URL, headers={"X-API-Key-ID": api_key},
                      files={"audio_file": (filename, audio_bytes, "audio/wav")}, data=data, timeout=60)
    ms = int((time.time() - t0) * 1000)
    if r.status_code != 200:
        raise RuntimeError(f"Speech-to-text failed ({r.status_code}): {r.text[:200]}")
    j = r.json()
    if not j.get("success", True):
        raise RuntimeError(f"Speech-to-text failed: {j}")
    return {"text": j.get("transcript", ""), "lang": j.get("detected_language_code") or
            (language_code if language_code != "indic-auto" else None),
            "model": j.get("model", model or "prisma-v2.5"), "stt_ms": ms}


def fix_wav(b):
    """Gnani streams WAVs with an 'unknown length' header; browsers can refuse those. Patch real sizes in."""
    if b[:4] != b"RIFF":
        return b
    i = b.find(b"data")
    if i < 0:
        return b
    b = bytearray(b)
    struct.pack_into("<I", b, 4, len(b) - 8)
    struct.pack_into("<I", b, i + 4, len(b) - (i + 8))
    return bytes(b)


def _tts_request(text, model, voice, lang, api_key, speed=1.0):
    body = {"text": text, "voice": voice, "model": model, "language": lang, "speed": float(speed),
            "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2,
                             "encoding": "linear_pcm", "container": "wav"}}
    return requests.post(TTS_URL, headers={"Content-Type": "application/json", "X-API-Key-ID": api_key},
                         json=body, timeout=60)


def synthesize(text, reply_lang="en", api_key=None):
    """Timbre text-to-speech (v3.0 first, automatic fallback to v2.5). Returns WAV bytes.
    Set TIMBRE_MODEL=timbre-v2.5 (or timbre-v3.0) in .env to force one model."""
    api_key = validate_gnani_api_key(api_key)
    forced = settings.get("TIMBRE_MODEL", "").strip()
    models = [m for m in TTS_MODELS if not forced or m[0] == forced] or TTS_MODELS
    start = _tts_choice["idx"] if _tts_choice["idx"] is not None and not forced else 0
    last = None
    for i in range(start, len(models)):
        model, voices = models[i]
        voice, lang = voices.get(reply_lang, voices["en"])
        r = _tts_request(text, model, voice, lang, api_key)
        if r.status_code == 200:
            _tts_choice["idx"] = i
            return fix_wav(r.content)
        last = f"{model}: {r.status_code} {r.text[:120]}"
    raise RuntimeError(f"Text-to-speech failed ({last})")


if __name__ == "__main__":
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(48000), w.writeframes(b"\x00\x01" * 4800)
    good = buf.getvalue()
    bad = bytearray(good)
    struct.pack_into("<I", bad, 4, 0xFFFFFFFF)
    j = bytes(bad).find(b"data")
    struct.pack_into("<I", bad, j + 4, 0xFFFFFFFF)
    fixed = fix_wav(bytes(bad))
    with wave.open(io.BytesIO(fixed)) as w:
        assert w.getnframes() == 4800, w.getnframes()
    print("fix_wav OK")
