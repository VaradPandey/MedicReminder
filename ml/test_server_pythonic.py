"""
MedicReminder ML Service - Prescription OCR API.
Serves POST /extract for handwritten prescription scanning via hosted vision models.
"""

import os
import time
import json
import uuid
import logging
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Configure standardized logging format once
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("OCR][ML")

# Load environment configuration from ml/.env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

from ocr_engine import PrescriptionOCREngine, PrescriptionOCRError

try:
    import disease_predictor
except Exception as _dp_err:
    logger.warning(f"Disease predictor import failed or deferred: {_dp_err}")
    disease_predictor = None

app = Flask(__name__)

allowed_origins = [
    "https://medicreminder.vercel.app",
    "https://medicreminder-backend.onrender.com",
    "https://medicreminder-ml.onrender.com",
    "https://medic-reminder-two.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    r"^https:\/\/.*medicreminder.*\.vercel\.app$",
]
CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

# Initialize OCR Engine
ocr_engine = PrescriptionOCREngine()


@app.route('/', methods=["GET"])
def home():
    ocr_engine.reload_config()
    return jsonify({
        "status": "online",
        "service": "MedicReminder ML & Prediction Service",
        "engine": ocr_engine.engine_mode,
        "model": ocr_engine.vision_model_id
    }), 200


@app.route('/health', methods=["GET"])
def health():
    ocr_engine.reload_config()
    return jsonify({
        "status": "ok",
        "service": "MedicReminder ML & Prediction Service",
        "engine": ocr_engine.engine_mode,
        "model": ocr_engine.vision_model_id
    }), 200


@app.route('/symptoms', methods=['GET'])
def symptoms_endpoint():
    if not disease_predictor:
        return jsonify({"error": "Disease predictor not available"}), 503
    res, code = disease_predictor.get_symptoms()
    return jsonify(res), code


@app.route('/predict', methods=['POST'])
def predict_endpoint():
    if not disease_predictor:
        return jsonify({"error": "Disease predictor not available"}), 503
    payload = request.get_json(silent=True) or {}
    symptoms = payload.get("symptoms", [])
    res, code = disease_predictor.predict(symptoms)
    return jsonify(res), code



@app.route('/extract', methods=['POST'])
def extract():
    t_start = time.time()
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())[:8]
    tmp_path = None

    logger.info(f"Request received request_id={req_id} method={request.method} path={request.path}")

    try:
        # Dynamically reload environment variables in case .env was updated
        load_dotenv(env_path, override=True)
        ocr_engine.reload_config()

        if 'image' not in request.files:
            logger.warning(f"Validation failed request_id={req_id} reason='no image field in request'")
            return jsonify({"status": 400, "error": "Image file is required in 'image' field"}), 400

        image_file = request.files['image']
        if not image_file or not image_file.filename:
            logger.warning(f"Validation failed request_id={req_id} reason='empty filename'")
            return jsonify({"status": 400, "error": "Image file is required"}), 400

        ext = os.path.splitext(image_file.filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'):
            logger.warning(f"Validation failed request_id={req_id} ext={ext} reason='unsupported file extension'")
            return jsonify({
                "status": 400,
                "error": f"Unsupported file type '{ext}'. Please upload an image file (PNG, JPG, JPEG, WEBP, BMP)."
            }), 400

        # Save temporarily for processing
        temp_dir = tempfile.gettempdir()
        filename = secure_filename(f"rx_{req_id}_{int(time.time()*1000)}_{image_file.filename}")
        tmp_path = os.path.join(temp_dir, filename)
        image_file.save(tmp_path)

        file_size = os.path.getsize(tmp_path)
        logger.info(
            f"File validated request_id={req_id} filename='{image_file.filename}' "
            f"ext='{ext}' size_bytes={file_size} model={ocr_engine.vision_model_id}"
        )

        # Execute OCR processing
        structured_data = ocr_engine.process_prescription(tmp_path)

        duration_ms = round((time.time() - t_start) * 1000)
        meds_count = len(structured_data.get("medications", []))
        logger.info(
            f"Extraction completed request_id={req_id} medicine_count={meds_count} "
            f"needs_review={structured_data.get('needs_review')} duration_ms={duration_ms} status=200"
        )

        return jsonify({
            "status": 200,
            "success": True,
            "result": json.dumps(structured_data)
        }), 200

    except PrescriptionOCRError as pe:
        duration_ms = round((time.time() - t_start) * 1000)
        logger.error(
            f"Extraction failed request_id={req_id} error_type='PrescriptionOCRError' "
            f"message='{str(pe)}' duration_ms={duration_ms} status={pe.status_code}"
        )
        return jsonify({"status": pe.status_code, "error": str(pe)}), pe.status_code

    except Exception as e:
        duration_ms = round((time.time() - t_start) * 1000)
        logger.error(
            f"Extraction failed request_id={req_id} error_type='{type(e).__name__}' "
            f"message='{str(e)}' duration_ms={duration_ms} status=500",
            exc_info=True
        )
        return jsonify({"status": 500, "error": f"Prescription processing failed: {str(e)}"}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting ML Prescription OCR Service on port {port}")
    app.run(host='0.0.0.0', port=port)
