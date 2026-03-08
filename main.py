from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
from io import BytesIO
import google.genai as genai
import os
import json
import re
from PIL import Image
from dotenv import load_dotenv
from openpyxl.utils import get_column_letter

# Load environment variables
env_file_loaded = "None"
if os.path.exists(".env"):
    load_dotenv(".env")
    env_file_loaded = ".env (root)"
elif os.path.exists("backend/.env"):
    load_dotenv("backend/.env")
    env_file_loaded = "backend/.env"
else:
    load_dotenv()
    env_file_loaded = "default"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"DEBUG: Loaded environment from: {env_file_loaded}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        key_preview = f"{GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-4:]}" if len(GEMINI_API_KEY) > 10 else "too short"
        print(f"DEBUG: Gemini Client initialized with key prefix: {key_preview}")
    else:
        client = None
        print("WARNING: GEMINI_API_KEY not found!")
except Exception as e:
    print(f"ERROR initializing Gemini client: {e}")
    client = None

PROMPT = """
You are an expert OCR and data extraction system.
Extract the contact details from this visiting card image and return ONLY valid JSON.
Do not wrap it in markdown block like ```json ... ```, just return the raw JSON string.

Fields to extract:
- "Company name"
- "Company address"
- "city"
- "state"
- "pincode"
- "Company owner name"
- "phone number"
- "email"
- "extra" (Any extra information not covered above should be placed here as a single string)

If a field is not found, leave it as an empty string.
JSON Format:
{
  "Company name": "",
  "Company address": "",
  "city": "",
  "state": "",
  "pincode": "",
  "Company owner name": "",
  "phone number": "",
  "email": "",
  "extra": ""
}
"""

@app.get("/api/health")
def health_check():
    return {"status": "ok", "gemini_ready": client is not None}

@app.post("/extract")
async def extract_card(file: UploadFile = File(...)):
    print(f"DEBUG: Received extraction request for file: {file.filename}")
    
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API key is not configured.")
        
    try:
        image_data = await file.read()
        img = Image.open(BytesIO(image_data))
        
        # Try different models in case of quota issues
        # Based on list_ids.py output: ['gemini-2.5-flash', 'gemini-2.0-flash-001', 'gemini-2.0-flash']
        models_to_try = [
            'gemini-2.5-flash', 
            'gemini-2.0-flash-001', 
            'gemini-2.0-flash'
        ]
        
        last_error = "Unknown error"
        
        for model_id in models_to_try:
            try:
                print(f"DEBUG: Trying extraction with model: {model_id}")
                response = client.models.generate_content(
                    model=model_id,
                    contents=[PROMPT, img]
                )
                
                if not response.text:
                    print(f"WARNING: Model {model_id} returned empty text.")
                    continue
                    
                text = response.text.strip()
                
                # Robust JSON extraction
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    text = json_match.group(0)
                else:
                    text = text.replace("```json", "").replace("```", "").strip()
                    
                data = json.loads(text)
                data["_filename"] = file.filename
                print(f"DEBUG: Extraction successful with model: {model_id}")
                return data
                
            except Exception as model_err:
                last_error = str(model_err)
                print(f"WARNING: Model {model_id} failed: {last_error}")
                # If it's a 429 or 404, we continue to try the next model
                if "429" in last_error or "404" in last_error or "quota" in last_error.lower() or "not found" in last_error.lower():
                    continue
                else:
                    # For other critical errors, we stop
                    break
        
        # If we got here, all models failed
        raise Exception(f"All models failed. Last error: {last_error}")
        
    except Exception as e:
        print(f"CRITICAL Extraction error: {e}")
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            error_msg = "Quota Exceeded: All available free-tier models have reached their daily limit. Please try again later or wait 60 seconds."
        
        raise HTTPException(status_code=500, detail=error_msg)

class ExcelRequest(BaseModel):
    data: List[Dict[str, Any]]

@app.post("/export-excel")
async def export_excel(payload: ExcelRequest):
    try:
        df = pd.DataFrame(payload.data)
        if "_filename" in df.columns:
            df = df.drop(columns=["_filename"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Contacts')
            worksheet = writer.book['Contacts']
            for i, column_cells in enumerate(worksheet.columns, 1):
                max_length = 0
                for cell in column_cells:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                worksheet.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=visiting_cards.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Static files mounting
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
