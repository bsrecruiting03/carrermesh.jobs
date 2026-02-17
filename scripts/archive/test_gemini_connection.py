
import sys
import os

# Add root to sys.path
sys.path.append("/app") # Docker container path
sys.path.append(os.getcwd()) # Local path fallback

try:
    from us_ats_jobs.intelligence.llm_extractor import LLMService
except ImportError:
    # Try local import style if running from root
    from us_ats_jobs.intelligence.llm_extractor import LLMService

def test_gemini():
    print("🚀 Testing Gemini Connection...")
    try:
        service = LLMService()
        print(f"🔹 Configured Provider: {service.provider}")
        
        if service.provider != "gemini":
            print(f"⚠️ Warning: LLM_PROVIDER is set to '{service.provider}', not 'gemini'.")
            print("Checking for Gemini keys anyway...")
            # Force verify if keys exist
            from us_ats_jobs.intelligence.llm_extractor import GEMINI_API_KEYS
            if GEMINI_API_KEYS:
                 print(f"✅ Found {len(GEMINI_API_KEYS)} Gemini Key(s) in env.")
            else:
                 print("❌ No Gemini Keys found in environment.")
            return

        if not service.client:
            print("❌ Client initialization failed. Check API Key or google-generativeai installation.")
            return

        print(f"🔹 Model: {service.client.model_name if hasattr(service.client, 'model_name') else 'Unknown'}")
        print("📨 Sending test request: 'Reply with Pong'...")
        
        # Test Generation
        response = service.generate_text("Reply with the single word: Pong")
        print(f"cw Response: {response.strip()}")
        
        if "Pong" in response or "pong" in response.lower():
            print("✅ Gemini API is working correctly!")
        else:
            print("✅ Gemini API responded, but content was unexpected.")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini()
