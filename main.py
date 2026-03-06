from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import pandas as pd
from io import BytesIO
from google import genai
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# You can set this in a .env file or environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"Loaded GEMINI_API_KEY: {'YES' if GEMINI_API_KEY else 'NO'}")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
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
    if not client:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured in backend.")
        
    try:
        image_data = await file.read()
        img = Image.open(BytesIO(image_data))
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=[PROMPT, img]
        )
        
        text = response.text.strip()
        # Clean up any potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        # Attach the filename so frontend knows which file this belongs to
        data["_filename"] = file.filename
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Contacts']
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value) or "") for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

        output.seek(0)
        
        from fastapi.responses import StreamingResponse
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
