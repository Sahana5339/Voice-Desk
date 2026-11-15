"""Server-side use cases that connect ticket logic to speech and language providers."""
import core
import hybrid
import settings
import syst

LANGS = syst.LANGS


def gnani_configured():
    return settings.gnani_configured()


def llm_configured():
    return hybrid.available()


def transcribe(audio_bytes, language_label, filename="audio.wav"):
    """Transcribe audio and apply the existing Hindi retry for auto-detection failures."""
    language_code, model = syst.LANGS[language_label]
    notes = []
    try:
        result = syst.transcribe(audio_bytes, language_code, model, filename=filename)
    except Exception as exc:
        if language_code != "indic-auto":
            raise
        notes.append(f"Auto-detect failed ({exc}); retried as Hindi. Pick the language in the sidebar if needed.")
        result = syst.transcribe(audio_bytes, "hi-IN", None, filename=filename)
    return result, notes


def synthesize(text, reply_lang):
    return syst.synthesize(text, reply_lang)


def make_ticket(transcript, lang_code, number, use_llm, history=None, overrides=None):
    if use_llm:
        return hybrid.make_ticket_hybrid(transcript, lang_code, number, history=history, overrides=overrides)
    return core.make_ticket(transcript, lang_code, number, history=history, overrides=overrides)
