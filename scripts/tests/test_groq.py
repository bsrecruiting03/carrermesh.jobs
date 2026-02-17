import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Correctly navigate from scripts/tests/test_groq.py to Project Root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(root_dir, '.env'))

LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MODEL = os.getenv("LLM_MODEL") or "llama-3.3-70b-versatile"

print(f"=== Testing All Groq Keys ===\n")
print(f"Endpoint: {LLM_BASE_URL}")
print(f"Model: {LLM_MODEL}")

# Parsing Keys
keys_str = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
if keys_str:
    all_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
else:
    all_keys = []

print(f"Found {len(all_keys)} keys to test.")

if not all_keys:
    print("❌ No keys found in .env!")
    sys.exit(1)

success_count = 0
fail_count = 0

for i, key in enumerate(all_keys):
    masked_key = key[:6] + "..." + key[-4:]
    print(f"\n🔑 Testing Key #{i+1}: {masked_key}")
    
    try:
        client = OpenAI(
            api_key=key,
            base_url=LLM_BASE_URL
        )
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.1,
            max_tokens=5
        )
        
        print(f"✅ SUCCESS! Response: {response.choices[0].message.content}")
        success_count += 1
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        fail_count += 1

print("\n" + "="*30)
print(f"Summary: {success_count} Working, {fail_count} Failed")
print("="*30)
