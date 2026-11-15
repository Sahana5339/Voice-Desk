"""Server-side configuration shared by the app and command-line tools."""
import os

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

_PLACEHOLDER_KEYS = {
    "your_key_here", "your_gnani_key_here", "your_api_key_here", "replace_me", "changeme",
    "example", "placeholder", "none", "null", "test_key", "demo_key", "sample_key",
}


def get(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default


def gnani_api_key(value=None):
    """Return a configured Gnani key or raise a clear configuration error."""
    key = (value or get("GNANI_API_KEY") or "").strip()
    lowered = key.lower()
    if (not key or lowered in _PLACEHOLDER_KEYS or lowered.startswith(("your_", "replace_", "demo_"))
            or ("example" in lowered and "key" in lowered)):
        raise RuntimeError(
            "GNANI_API_KEY is missing or still contains a placeholder value. Set a real Gnani key in .env or "
            "Streamlit Secrets."
        )
    return key


def gnani_configured():
    try:
        gnani_api_key()
    except RuntimeError:
        return False
    return True
