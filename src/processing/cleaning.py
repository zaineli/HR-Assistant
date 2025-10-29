"""
Text cleaning and PII redaction utilities.
"""
import re
import unicodedata

def redact_pii(text):
    text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[REDACTED_EMAIL]', text)
    text = re.sub(r'\b\d{10,}\b', '[REDACTED_PHONE]', text)
    return text

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def clean_whitespace(text):
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()
