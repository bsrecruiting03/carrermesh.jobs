
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load config
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://api.x.ai/v1"
LLM_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL") or "grok-beta"

print(f"Testing Grok API...")
print(f"Base URL: {LLM_BASE_URL}")
print(f"Model: {LLM_MODEL}")
print(f"API Key: {LLM_API_KEY[:8]}...")

try:
    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    print("\n--- Testing Generation ---")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Grok is working!' in JSON format with a key 'message'."}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    result = response.choices[0].message.content
    print(f"\n✅ Success!")
    print(f"Response: {result}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
