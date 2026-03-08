# AI Visiting Card Extractor

An automated system to extract contact details from visiting cards using Google's Gemini AI. It converts images into structured data and allows exporting to Excel.

## 🚀 How to Run the Project

### 1. Setup the Backend
The backend handles the AI processing and Excel generation.

1.  Open your terminal in the `backend` folder:
    ```bash
    cd backend
    ```
2.  Install dependencies (if not already done):
    ```bash
    pip install -r requirements.txt
    ```
3.  Ensure your API Key is set:
    - Create a file named `.env` in the `backend` folder.
    - Add your key: `GEMINI_API_KEY=your_actual_key_here`
4.  Start the server:
    ```bash
    python -m uvicorn main:app --reload
    ```
    *The server will be live at http://127.0.0.1:8000*

### 2. Run the Frontend
The frontend provides a beautiful interface to upload and view data.

1.  Navigate to the `frontend` folder.
2.  Open **`index.html`** in any modern web browser (Chrome, Edge, etc.).
    - *Tip: You can just right-click the file in VS Code and select "Open with Live Server" if you have that extension, or just double-click it in your file explorer.*

## 🛠 Features
- **Parallel Processing**: Upload multiple cards at once.
- **AI-Powered OCR**: Uses Gemini 2.0 Flash for high-accuracy extraction.
- **Instant Preview**: See the card image right next to the data.
- **Excel Export**: Download all extracted data with one click.
- **Secure**: Sensitive keys are kept local and never shared.

## 📦 Tech Stack
- **Backend**: FastAPI (Python)
- **AI**: Google Gemini Pro (Generative AI SDK)
- **Frontend**: Vanilla HTML/JS with CSS Glassmorphism
- **Data**: Pandas & OpenPyXL
