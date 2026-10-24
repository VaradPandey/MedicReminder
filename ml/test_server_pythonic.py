from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import base64
import json
import os
import tempfile
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# Load environment configuration from ml/.env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

app = Flask(__name__)

allowed_origins = [
    "https://medic-reminder-two.vercel.app",
    "https://medicreminder-production-aaca.up.railway.app",
    "https://medicreminder-production-0f69.up.railway.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]
CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

def get_ai_client(api_key: str = None, base_url: str = None) -> OpenAI:
    """Instantiate OpenAI-compatible client for Groq or custom base URL."""
    key = api_key or os.getenv("GROQ_API_KEY") or "missing-key"
    url = base_url or os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    return OpenAI(base_url=url, api_key=key)

def extract_text_from_image(image_path: str) -> str:
    """
    Extracts raw text from an image file using:
    1. Windows Media OCR (built-in on Windows 10/11, fast and accurate)
    2. pytesseract (if Tesseract binary is installed or on Linux/macOS)
    """
    # 1. Windows Media OCR (preferred on Windows)
    try:
        import winocr
        with Image.open(image_path) as img:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                ocr_res = loop.run_until_complete(winocr.recognize_pil(img))
                if ocr_res and hasattr(ocr_res, "text") and ocr_res.text.strip():
                    return ocr_res.text.strip()
            finally:
                loop.close()
    except Exception:
        pass

    # 2. pytesseract fallback
    try:
        import pytesseract
        tess_cmd = os.getenv("TESSERACT_CMD")
        if tess_cmd:
            pytesseract.pytesseract.tesseract_cmd = tess_cmd
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                return text.strip()
    except Exception:
        pass

    return ""

def is_vision_model(model_name: str) -> bool:
    name = (model_name or "").lower()
    return "vision" in name or "muse-spark" in name or "qwen3.6" in name or "qwen3.8" in name

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

@app.route('/', methods=["GET"])
def home():
    return "<h1>Hello, this is Flask Pythonic Backend responding</h1>"

@app.route('/extract', methods=['POST'])
def extract():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "image file is required"}), 400

        image_file = request.files['image']
        if not image_file.filename:
            return jsonify({"error": "image file is required"}), 400

        ext = os.path.splitext(image_file.filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.pdf'):
            return jsonify({"error": f"Unsupported file type '{ext}'. Please upload an image file (PNG, JPG, JPEG, WEBP)."}), 400

        temp_dir = tempfile.gettempdir()
        filename = secure_filename(image_file.filename or 'upload.jpg')
        tmp_path = os.path.join(temp_dir, filename)
        image_file.save(tmp_path)

        # Support mock mode only if explicitly enabled
        if os.getenv("MOCK_OCR", "").lower() in ("true", "1", "yes"):
            mock_prescription = {
                "patientName": "Jane Doe",
                "doctorName": "Dr. Sarah Mitchell",
                "dateIssued": "2026-10-24",
                "diagnosis": "Respiratory Tract Infection",
                "medications": [
                    {
                        "name": "Amoxicillin",
                        "dosage": "500mg",
                        "frequency": "Twice daily",
                        "duration": "7 days",
                        "instructions": "Take after meals"
                    },
                    {
                        "name": "Paracetamol",
                        "dosage": "650mg",
                        "frequency": "As needed",
                        "duration": "3 days",
                        "instructions": "For fever and body ache"
                    }
                ]
            }
            return jsonify({"result": json.dumps(mock_prescription)}), 200

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return jsonify({
                "error": "GROQ_API_KEY is not configured in ml/.env. Please configure your Groq API key."
            }), 500

        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        client = get_ai_client(api_key, base_url)

        # Check if model supports direct multimodal vision
        if is_vision_model(model):
            base64_image = encode_image(tmp_path)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a medical OCR assistant. Extract prescriptions from images and return "
                        "structured JSON matching this schema:\n"
                        "{\n"
                        '  "patientName": "string",\n'
                        '  "doctorName": "string",\n'
                        '  "dateIssued": "string",\n'
                        '  "diagnosis": "string",\n'
                        '  "medications": [\n'
                        '    {"name": "string", "dosage": "string", "frequency": "string", "duration": "string", "instructions": "string"}\n'
                        "  ]\n"
                        "}\n"
                        "Return ONLY valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract prescription details from this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
        else:
            # Text-only model (e.g. openai/gpt-oss-20b): extract raw text first
            extracted_text = extract_text_from_image(tmp_path)
            if not extracted_text:
                return jsonify({
                    "error": "No readable text could be recognized from the uploaded prescription image. Please ensure the image is clear, focused, and contains readable text."
                }), 422

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a medical prescription parser assistant. Parse the provided OCR text and return "
                        "structured JSON matching this schema:\n"
                        "{\n"
                        '  "patientName": "string",\n'
                        '  "doctorName": "string",\n'
                        '  "dateIssued": "string",\n'
                        '  "diagnosis": "string",\n'
                        '  "medications": [\n'
                        '    {"name": "string", "dosage": "string", "frequency": "string", "duration": "string", "instructions": "string"}\n'
                        "  ]\n"
                        "}\n"
                        "Return ONLY the JSON object. Do not include markdown preamble or conversational text."
                    )
                },
                {
                    "role": "user",
                    "content": f"Parse the prescription details from this recognized text:\n\n{extracted_text}"
                }
            ]

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1
            )
        except Exception as e:
            return jsonify({
                "error": f"Groq AI provider error: {str(e)}"
            }), 502

        if not hasattr(response, "choices") or not response.choices:
            return jsonify({
                "error": "Groq AI provider returned an empty or invalid completion response."
            }), 502

        content = response.choices[0].message.content or ""
        return jsonify({"result": content}), 200

    except Exception as e:
        return jsonify({"error": f"Prescription processing failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
