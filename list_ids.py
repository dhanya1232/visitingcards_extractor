import google.genai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    for model in client.models.list():
        m_name = model.name
        if m_name.startswith("models/"): 
            m_name = m_name[7:]
        print(m_name)
except Exception as e:
    print(f"Error: {e}")
