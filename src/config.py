"""
Configuration loader for pipeline settings.
"""
import os
from dotenv import load_dotenv


load_dotenv()

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

def _make_abs(path):
	if os.path.isabs(path):
		return path
	return os.path.join(_CONFIG_DIR, path)

RAW_DIR = _make_abs(os.getenv("RAW_DIR", "NOT_FOUND"))
FINAL_JSON = _make_abs(os.getenv("FINAL_JSON", "NOT_FOUND"))
LOG_FILE = _make_abs(os.getenv("LOG_FILE", "NOT_FOUND"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "NOT_FOUND")

