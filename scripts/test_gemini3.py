#!/usr/bin/env python3
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import google.generativeai as genai
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=key)

test_models = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-pro-latest"
]

print("=" * 60)
print("TESTING GEMINI 3 FAMILY MODELS ON LIVE API KEY:")
print("=" * 60)

selected_model = None
for m_name in test_models:
    try:
        model = genai.GenerativeModel(m_name)
        res = model.generate_content("Neuromarketing scanpath analysis ping. Confirm in 5 words.")
        print(f"[SUCCESS] Model: '{m_name}' -> Response: {res.text.strip()}")
        if not selected_model:
            selected_model = m_name
    except Exception as e:
        print(f"[FAILED] Model: '{m_name}' -> Error: {e}")

print("=" * 60)
print(f"RECOMMENDED MODEL FOR .ENV: {selected_model}")
print("=" * 60)
