
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load config
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

LLM_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL") or "gemini-2.0-flash"

print(f"=== Testing Gemini 2.0 Flash ===\n")
print(f"Model: {LLM_MODEL}")
print(f"API Key: {LLM_API_KEY[:8]}...")

try:
    genai.configure(api_key=LLM_API_KEY)
    
    print("\n--- Test: Simple Generation ---")
    model = genai.GenerativeModel(LLM_MODEL)
    response = model.generate_content("Say 'Gemini is ready!' and nothing else.")
    
    print(f"✅ Success!")
    print(f"Response: {response.text}")
    
    print("\n--- Test: JSON Structured Output ---")
    response = model.generate_content(
        'Return this exact JSON: {"status": "working", "provider": "gemini"}',
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    
    print(f"✅ JSON Response: {response.text}")
    print(f"\n=== ✅ All Tests Passed! Gemini is ready for production. ===")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    if "429" in str(e) or "quota" in str(e).lower():
        print("\n⚠️ Quota issue still present. Need to:")
        print("1. Wait for Google to activate Free Tier (can take 24-48h for new keys)")
        print("2. Enable billing in Google Cloud Console")
        print("3. Use a different provider temporarily")
    sys.exit(1)
