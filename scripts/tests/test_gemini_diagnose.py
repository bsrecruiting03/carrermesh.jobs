
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env explicilty
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(root_dir, '.env')
load_dotenv(dotenv_path)

api_key = os.getenv("LLM_API_KEY") 
print(f"API Key found: {api_key[:8]}...")

if not api_key:
    print("ERROR: No API Key")
    sys.exit(1)

genai.configure(api_key=api_key)

print("\n--- Listing Models ---")
try:
    for m in genai.list_models():
        print(f"Model: {m.name}")
        print(f"Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"List Models Failed: {e}")

print("\n--- Testing Generation ---")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Attempting 'gemini-1.5-flash'...")
    response = model.generate_content("Hello")
    print("Success!")
    print(response.text)
except Exception as e:
    print(f"Flash Failed: {e}")

try:
    model = genai.GenerativeModel('gemini-pro')
    print("\nAttempting 'gemini-pro'...")
    response = model.generate_content("Hello")
    print("Success!")
    print(response.text)
except Exception as e:
    print(f"Pro Failed: {e}")
