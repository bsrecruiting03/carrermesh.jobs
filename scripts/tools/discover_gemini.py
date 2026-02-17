import google.generativeai as genai
import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

API_KEY = os.getenv('GEMINI_API_KEY')
print(f"Using API Key: {API_KEY[:5]}...{API_KEY[-5:]}")

genai.configure(api_key=API_KEY)

try:
    print("\n--- AVAILABLE MODELS ---")
    models = genai.list_models()
    for m in models:
        print(f"Name: {m.name} | Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
