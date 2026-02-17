
import os
import sys
import requests
from dotenv import load_dotenv

# Load config
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

LLM_API_KEY = os.getenv("LLM_API_KEY")

print("=== Grok API Diagnostic ===\n")
print(f"API Key format: {LLM_API_KEY[:8]}...{LLM_API_KEY[-4:]}")
print(f"Key length: {len(LLM_API_KEY)}")
print(f"Key prefix: {LLM_API_KEY[:4]}")

# Test 1: Basic endpoint check
print("\n--- Test 1: List Models Endpoint ---")
try:
    response = requests.get(
        "https://api.x.ai/v1/models",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        models = response.json()
        print(f"✅ Available models: {[m.get('id') for m in models.get('data', [])]}")
    else:
        print(f"❌ Error Response: {response.text}")
except Exception as e:
    print(f"❌ Request failed: {e}")

# Test 2: Simple chat completion
print("\n--- Test 2: Chat Completion ---")
try:
    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "grok-beta",
            "messages": [
                {"role": "user", "content": "Say hello"}
            ],
            "max_tokens": 50
        },
        timeout=30
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {result['choices'][0]['message']['content']}")
    else:
        print(f"❌ Error: {response.json()}")
except Exception as e:
    print(f"❌ Request failed: {e}")

print("\n=== Diagnostic Complete ===")
print("\nIf both tests fail with 400/401:")
print("1. Verify key is copied correctly from console.x.ai")
print("2. Check if billing/payment method is required")
print("3. Ensure API access is enabled for your account")
