"""
Gemini parsing and experience duration calculation.
"""
import json
import re
import time
from datetime import datetime
from dateutil import parser
from google import genai
from google.genai import types

# Handle both relative and absolute imports
try:
    from ..config import GOOGLE_API_KEY
except ImportError:
    from src.config import GOOGLE_API_KEY

client = genai.Client(api_key=GOOGLE_API_KEY)


def call_gemini_with_retry(prompt, model_primary="gemini-2.0-flash-lite", max_retries=3, wait_times=None):
    if wait_times is None:
        wait_times = [1, 2, 4]
    attempts = 0
    while attempts < max_retries:
        try:
            resp = client.models.generate_content(
                model=model_primary,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0)
            )
            if resp.text is not None:
                return resp.text.strip()
            else:
                return ""
        except Exception as e:
            if "503" in str(e) or "overloaded" in str(e):
                wait = wait_times[min(attempts, len(wait_times)-1)]
                time.sleep(wait)
                attempts += 1
            else:
                print(f"Gemini API error: {e}")
                raise e
    try:
        resp = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0)
        )
        if resp.text is not None:
            return resp.text.strip()
        else:
            return ""
    except Exception as e:
        print(f"Gemini fallback error: {e}")
        return None

def parse_cv_with_gemini(text):
    prompt = f"""
Extract structured CV information in this JSON format:
{{
  "name": "",
  "education": [{{"degree":"","field":"","university":"","country":"","start":null,"end":null,"gpa":null,"scale":null}}],
  "experience": [{{"title":"","org":"","start":null,"end":null,"duration_months":null,"domain":""}}],
  "publications": [{{"title":"","venue":"","year":null,"type":"","authors":[],"author_position":null,"journal_if":null,"domain":""}}],
  "awards": [{{"title":"","issuer":"","year":null,"type":""}}]
}}
RULES:
1. Extract the full name of the person from the resume and put it in the "name" field.
2. For experience, if end date missing, set "end": "currently working".
3. For education, include only Bachelor's or university-level degree or higher.
4. Return ONLY valid JSON.
"""
    raw = call_gemini_with_retry(prompt + text)
    if not raw:
        return {"name": "", "education": [], "experience": [], "publications": [], "awards": []}
    try:
        return json.loads(raw)
    except Exception as e:
        print(f"Error parsing Gemini JSON: {e}")
        c = raw[raw.find("{"): raw.rfind("}")+1]
        c = re.sub(r',\s*([}\]])', r'\1', c)
        try:
            return json.loads(c)
        except Exception as e2:
            print(f"Error parsing fallback JSON: {e2}")
            return {"name": "", "education": [], "experience": [], "publications": [], "awards": []}

def calculate_duration_months(start, end):
    try:
        start_date = parser.parse(start)
        if end == "currently working":
            end_date = datetime.now()
        else:
            try:
                end_date = parser.parse(end)
            except Exception as e:
                print(f"Error parsing end date '{end}': {e}")
                return None
        delta = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        return max(delta, 0)
    except Exception as e:
        print(f"Error parsing start date '{start}': {e}")
        return None
