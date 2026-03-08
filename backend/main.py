from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

# Load environment variables from .env in the same directory as this file
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment!")
else:
    print(f"DEBUG: GEMINI_API_KEY loaded successfully (starts with {GEMINI_API_KEY[:5]}...).")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("DEBUG: Gemini Client initialized.")
    else:
        client = None
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

@app.get("/")
def read_root():
    return {"message": "Backend is running! Please open frontend/index.html in your browser to use the application. You can view the API documentation at http://127.0.0.1:8000/docs"}


@app.post("/extract")
async def extract_card(file: UploadFile = File(...)):
    print(f"DEBUG: Received extraction request for file: {file.filename}")
    
    if not client:
        print("ERROR: API Client not initialized.")
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured or client failed to initialize.")
        
    try:
        image_data = await file.read()
        print(f"DEBUG: File read successfully. Size: {len(image_data)} bytes")
        
        img = Image.open(BytesIO(image_data))
        print(f"DEBUG: Image opened with PIL: {img.format}, {img.size}")
        
        print("DEBUG: Sending request to Gemini AI...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[PROMPT, img]
        )
        
        if not response.text:
            print("ERROR: Empty response from Gemini AI.")
            raise Exception("Gemini AI returned no text.")
            
        text = response.text.strip()
        print(f"DEBUG: Raw response received (first 100 chars): {text[:100]}...")
        
        # Robust JSON extraction using regex
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
            print("DEBUG: Found JSON block using regex.")
        else:
            # Fallback for simple stripping
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
        data = json.loads(text.strip())
        # Attach the filename so frontend knows which file this belongs to
        data["_filename"] = file.filename
        print(f"DEBUG: Successfully parsed JSON data for {file.filename}")
        return data
        
    except Exception as e:
        print(f"CRITICAL ERROR during extraction: {str(e)}")
        # Provide more detail back to the user
        error_detail = f"AI Error: {str(e)}"
        if "401" in str(e) or "API key" in str(e).lower():
            error_detail = "API Key Error: Your Gemini API Key appears to be invalid or expired."
        elif "quota" in str(e).lower():
            error_detail = "Quota Exceeded: You have reached your Gemini API limit."
            
        raise HTTPException(status_code=500, detail=error_detail)

class ExcelRequest(BaseModel):
    data: List[Dict[str, Any]]

@app.post("/export-excel")
async def export_excel(payload: ExcelRequest):
    try:
        # Create DataFrame from the list of dictionaries
        df = pd.DataFrame(payload.data)
        
        # Remove custom fields used in UI
        if "_filename" in df.columns:
            df = df.drop(columns=["_filename"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Contacts')
            
            # Access the workbook and sheet for formatting
            workbook = writer.book
            worksheet = workbook['Contacts']
            
            # Auto-adjust column widths
            for i, column_cells in enumerate(worksheet.columns, 1):
                max_length = 0
                for cell in column_cells:
                    try:
                        if cell.value:
                            val_len = len(str(cell.value))
                            if val_len > max_length:
                                max_length = val_len
                    except:
                        pass
                
                # Add a little buffer for padding
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[get_column_letter(i)].width = min(adjusted_width, 50) # Cap at 50 chars for readability

        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=visiting_cards.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}
