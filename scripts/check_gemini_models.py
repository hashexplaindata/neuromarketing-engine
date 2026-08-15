#!/usr/bin/env python3
import os
import google.generativeai as genai
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=key)

print("=" * 60)
print("AVAILABLE GENERATION MODELS IN GOOGLE AI STUDIO CATALOG:")
print("=" * 60)
models = []
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        name = m.name.replace("models/", "")
        models.append(name)
        print(f" - {name}")

print("=" * 60)
# Test candidates
candidates = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-2.0-pro-exp-02-05",
    "gemini-3.7-flash-video-understanding-eap"
]

print("\nTESTING CANDIDATE MODELS FOR GENERATION QUOTA & SPEED:")
for cand in candidates:
    if cand in models:
        try:
            m = genai.GenerativeModel(cand)
            res = m.generate_content("Ping. Respond with 'OK'.")
            print(f"✓ [{cand}] LIVE & RESPONDING: {res.text.strip()}")
            break
        except Exception as e:
            print(f"✗ [{cand}] Status: {e}")
