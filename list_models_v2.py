import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

print("Listing available models...")
try:
    for model in client.models.list():
        print(f"Model ID: {model.name}")
except Exception as e:
    print(f"Error listing models: {e}")
