"""
Logging utility for pipeline steps.
"""
from datetime import datetime
import os

# Handle both relative and absolute imports
try:
    from .config import LOG_FILE
except ImportError:
    from src.config import LOG_FILE

def log_step(message: str):
    """Append message with timestamp to log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
