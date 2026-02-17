
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load config
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:8b")

print("=== Ollama Connection Test ===\n")
print(f"Endpoint: {LLM_BASE_URL}")
print(f"Model: {LLM_MODEL}")

try:
    client = OpenAI(
        api_key="ollama",  # Ollama doesn't validate keys
        base_url=LLM_BASE_URL
    )
    
    print("\n--- Test 1: List Models ---")
    models = client.models.list()
    print(f"✅ Available models:")
    for model in models.data:
        print(f"  - {model.id}")
    
    print(f"\n--- Test 2: Simple Generation ---")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Ollama is working!' and nothing else."}
        ],
        temperature=0.1
    )
    
    result = response.choices[0].message.content
    print(f"✅ Response: {result}")
    
    print(f"\n--- Test 3: JSON Mode ---")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a JSON generator. Return only valid JSON."},
            {"role": "user", "content": 'Return JSON: {"status": "working", "model": "qwen2.5"}'}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    result = response.choices[0].message.content
    print(f"✅ JSON Response: {result}")
    
    print("\n=== ✅ All Tests Passed! ===")
    print("Ollama is ready for job enrichment.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Is Ollama running? Check: ollama serve")
    print("2. Is qwen2.5:8b pulled? Run: ollama pull qwen2.5:8b")
    print("3. Check Ollama logs for errors")
    sys.exit(1)
