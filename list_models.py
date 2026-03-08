import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

print("Listing available models...")
try:
    models = client.models.list()
    for model in models:
        print(f"Model: {model.name}, Supported Actions: {model.supported_actions}")
except Exception as e:
    print(f"Error listing models: {e}")
