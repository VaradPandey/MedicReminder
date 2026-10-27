# MedicReminder — Medical Prescription Vision OCR Service

This microservice provides multimodal vision-based handwritten medical prescription recognition and structured medication entity extraction for the MedicReminder (LifeAura AI) application.

---

## 1. Active Architecture & Provider Configuration

The service utilizes **Google Gemini** multimodal vision API as the primary, production-ready prescription OCR engine:

- **Provider**: Google Gemini (`VISION_PROVIDER=gemini`)
- **Active Model**: `gemini-flash-lite-latest` (fast 1–4 second inference latency)
- **Base Endpoint**: Google Generative Language OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`)
- **Key Capabilities**: Transcribes handwritten cursive prescriptions, extracting patient name, doctor name, issue date, diagnosis, and medications (name, strength, dosage, frequency, duration, instructions) with high accuracy.
- **Safety Gate & Review**: Enforces `needs_review: true` on all extractions. The frontend requires explicit user verification before saving or scheduling medicines.
- **Pluggable Fallback Providers**: The underlying engine (`ocr_engine.py`) also supports OpenAI (`gpt-4o-mini`) and OpenRouter as alternative configurable providers.

---

## 2. End-to-End Pipeline & Logging Flow

```mermaid
graph TD
    A[User Selects Prescription] -->|1. [OCR][FRONTEND] File Validation & Upload| B[React Frontend]
    B -->|2. [OCR][BACKEND] Forward with X-Request-Id| C[Express Backend Proxy]
    C -->|3. [OCR][ML] Validate Multipart & Size| D[Flask ML Service:5000]
    D -->|4. [OCR][ENGINE] Preprocess & Encode Base64| E[PrescriptionOCREngine]
    E -->|5. Vision API Request| F[Google Gemini Vision API]
    F -->|6. JSON Response| E
    E -->|7. Parse & Normalize Entities| D
    D -->|8. { status: 200, success: true, result }| C
    C -->|9. Pass JSON to Client| B
    B -->|10. Interactive Review & User Confirmation| G[User Review UI]
```

### Structured Terminal Logging Hierarchy

All components emit standardized, timestamped logs with dedicated prefixes without leaking patient data or API keys:

- `[OCR][FRONTEND]` (`upload.jsx`): File selection, validation, duplicate click prevention, scan duration, and verification state.
- `[OCR][BACKEND]` (`prescription.controller.js`): Incoming upload request, correlation ID (`X-Request-Id`), forwarding duration, and response status.
- `[OCR][ML]` (`test_server_pythonic.py`): Request receipt, correlation ID, file type/size validation, extraction status, and medicine count.
- `[OCR][ENGINE]` (`ocr_engine.py`): Image preprocessing, base64 encoding, Gemini vision API request dispatch, duration, structured JSON parsing, and unreadable field counts.

---

## 3. Environment Variables (`ml/.env`)

Configure the following variables in `ml/.env`:

```bash
# Active Vision Provider: 'gemini', 'openai', or 'openrouter'
VISION_PROVIDER=gemini

# Google Gemini Configuration (Recommended Production Provider: 1-4s latency)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_ID=gemini-flash-lite-latest

# Service Port
PORT=5000

# Offline Mock Mode (Optional for local testing without calling API)
# MOCK_OCR=false
```

---

## 4. Setup and Startup Commands

### Install Dependencies
```bash
cd ml
.\.venv\Scripts\pip.exe install -r requirements.txt
```

### Start the Service
```bash
cd ml
.\.venv\Scripts\python.exe test_server_pythonic.py
```
Or via the entrypoint alias:
```bash
python app.py
```

### Run Automated Tests
```bash
cd ml
.\.venv\Scripts\python.exe -m unittest tests/test_ocr_service.py
```

### Run Benchmark Evaluation
```bash
cd ml
# Synthetic benchmark sample
.\.venv\Scripts\python.exe evaluate_ocr.py --benchmark

# Real prescription sample
.\.venv\Scripts\python.exe evaluate_ocr.py --image "prescriptions/presc1.png"
```

---

## 5. Structured Output Schema

The service returns a strict JSON payload:

```json
{
  "status": 200,
  "success": true,
  "result": "{\"patientName\": \"Mr. Aman\", \"doctorName\": \"Dr. Sachin Patil\", \"dateIssued\": \"22/05/25\", \"diagnosis\": \"Cold, fever\", \"medications\": [{\"name\": \"Tab. Opor-CW\", \"strength\": \"200mg\", \"dosage\": \"1 tablet\", \"frequency\": \"Once daily\", \"duration\": \"6 days\", \"instructions\": \"\", \"confidence\": 0.85}], \"unreadable_fields\": [], \"needs_review\": true, \"engine_used\": \"gemini\", \"model\": \"gemini-flash-lite-latest\", \"latency_sec\": 2.50}"
}
```
