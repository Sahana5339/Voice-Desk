"""Check which Timbre model/voice works for your key. Usage: python probe_tts.py   (needs GNANI_API_KEY in .env)"""
import os
from dotenv import load_dotenv
import syst

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
key = os.environ.get("GNANI_API_KEY", "").strip()
if not key:
    raise SystemExit("Add GNANI_API_KEY to .env first.")
TEXT = {"en": "Your complaint has been registered.", "hi": "आपकी शिकायत दर्ज हो गई है।", "kn": "ನಿಮ್ಮ ದೂರು ದಾಖಲಾಗಿದೆ."}
for model, voices in syst.TTS_MODELS:
    for lang, (voice, code) in voices.items():
        r = syst._tts_request(TEXT[lang], model, voice, code, key)
        print(f"{model:12} {lang} voice={voice:8} -> {'OK ' + str(len(r.content)) + ' bytes' if r.status_code == 200 else 'FAIL ' + str(r.status_code) + ' ' + r.text[:100]}")
        if r.status_code == 200:
            open(f"probe_{model}_{lang}.wav", "wb").write(syst.fix_wav(r.content))
