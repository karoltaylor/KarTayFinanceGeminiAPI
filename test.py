import google.generativeai as genai
from src.config.settings import Settings

# Configure with API key
api_key = Settings.GOOGLE_API_KEY
if not api_key or api_key == "your_google_api_key_here":
    print("Error: GOOGLE_API_KEY not set!")
    print("Please add your API key to src/config/settings.py")
    exit()

genai.configure(api_key=api_key)

print("Listing available Gemini models...")
print("=" * 60)

try:
    # List all available models
    for model in genai.list_models():
        # Check if model supports generateContent
        if "generateContent" in model.supported_generation_methods:
            print(f"[OK] {model.name}")
            print(f"     Display Name: {model.display_name}")
            print(f"     Description: {model.description[:80]}...")
            print()
        else:
            print(f"[--] {model.name} (does not support generateContent)")

    print("=" * 60)
    print("\nRecommended models for this project:")
    print("  - models/gemini-1.5-pro-latest")
    print("  - models/gemini-1.5-flash-latest")
    print("  - models/gemini-pro")

except Exception as e:
    print(f"Error listing models: {e}")
