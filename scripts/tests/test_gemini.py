
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env directly
load_dotenv('../.env')

api_key = os.getenv("GEMINI_API_KEY")
print(f"DEBUG: Key length: {len(api_key) if api_key else 0}")

genai.configure(api_key=api_key)

print("\n--- TEST 1: LIST MODELS ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- TEST 2: GENERATE CONTENT (gemini-2.0-flash-exp) ---")
try:
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    response = model.generate_content("Say hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error 2.0: {e}")

print("\n--- TEST 3: GENERATE CONTENT (models/gemini-2.0-flash-exp) ---")
try:
    model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
    response = model.generate_content("Say hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error 2.0 (prefixed): {e}")

print("\n--- TEST 4: GENERATE CONTENT (gemini-1.5-flash) ---")
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error 1.5: {e}")
