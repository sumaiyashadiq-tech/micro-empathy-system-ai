"""Language helpers for the browser-based Web Speech API prototype."""


SPEECH_LOCALES = {
    "en": "en-IN",
    "ta": "ta-IN",
}


def speech_locale(language: str) -> str:
    """Translate the app's language code to a browser SpeechRecognition locale."""
    return SPEECH_LOCALES.get(language, SPEECH_LOCALES["en"])
