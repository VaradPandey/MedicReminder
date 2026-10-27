"""
Evaluation and Benchmarking Tool for Medical Prescription OCR.
Benchmarks the active Google Gemini (or configured) multimodal vision pipeline.
"""

import os
import sys
import time
import json
import argparse
from typing import Dict, Any
from PIL import Image, ImageDraw
from dotenv import load_dotenv

# Load ml/.env if present
load_dotenv()

# Ensure UTF-8 stdout on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from image_preprocessor import preprocess_prescription_image, validate_image_file
from ocr_engine import PrescriptionOCREngine, PrescriptionOCRError

def create_synthetic_sample(output_path: str) -> str:
    """Creates a sample realistic prescription for standardized benchmarking."""
    img = Image.new("RGB", (900, 600), color=(252, 250, 244))
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((60, 40), "CITY MULTISPECIALITY CLINIC", fill=(20, 20, 60))
    draw.text((60, 65), "Dr. Rajesh Sharma, MD (Medicine) | Reg: MCI-48291", fill=(40, 40, 40))
    draw.text((60, 85), "Phone: +91 98765 43210 | New Delhi", fill=(70, 70, 70))
    draw.line([(60, 115), (840, 115)], fill=(120, 120, 120), width=2)
    
    # Patient info
    draw.text((60, 130), "Patient: Vikram Malhotra", fill=(30, 30, 30))
    draw.text((450, 130), "Age: 52 Y / M", fill=(30, 30, 30))
    draw.text((700, 130), "Date: 24/10/2026", fill=(30, 30, 30))
    draw.text((60, 160), "Diagnosis: Acute Bronchitis, Fever", fill=(50, 50, 50))
    draw.line([(60, 190), (840, 190)], fill=(180, 180, 180), width=1)
    
    # Prescription lines
    draw.text((60, 210), "Rx", fill=(10, 10, 50))
    draw.text((100, 250), "1. Tab. Augmentin 625mg  ---  1-0-1  x 5 days (After food)", fill=(20, 30, 80))
    draw.text((100, 300), "2. Tab. Pan-D  ---  1-0-0  x 5 days (Before breakfast)", fill=(20, 30, 80))
    draw.text((100, 350), "3. Tab. Dolo 650mg  ---  1-1-1  x 3 days SOS (For fever)", fill=(20, 30, 80))
    draw.text((100, 400), "4. Syp. Ascoril-D  ---  10ml TDS  x 5 days", fill=(20, 30, 80))
    draw.text((100, 450), "5. Tab. Montair-LC  ---  0-0-1  x 7 days (Bedtime)", fill=(20, 30, 80))
    
    # Footer
    draw.line([(60, 510), (840, 510)], fill=(180, 180, 180), width=1)
    draw.text((60, 525), "Advise: Adequate rest, steam inhalation twice daily.", fill=(60, 60, 60))
    draw.text((650, 545), "Dr. R. Sharma (Signed)", fill=(20, 30, 70))
    
    img.save(output_path)
    return output_path

def evaluate_prescription(image_path: str, engine: PrescriptionOCREngine) -> Dict[str, Any]:
    """Runs evaluation using the active multimodal vision model."""
    results: Dict[str, Any] = {}
    
    # 1. Image Preprocessing Analysis
    t_prep_start = time.time()
    _, prep_meta = preprocess_prescription_image(image_path)
    t_prep = time.time() - t_prep_start
    
    results["image_metadata"] = {
        "file": os.path.basename(image_path),
        "original_size": prep_meta.get("original_size"),
        "processed_size": prep_meta.get("processed_size"),
        "preprocessing_time_sec": round(t_prep, 3)
    }

    # 2. Multimodal Vision OCR Engine
    t_vision_start = time.time()
    try:
        json_str = engine.image_to_prescription_json(image_path)
        t_vision = time.time() - t_vision_start
        parsed = json.loads(json_str)

        results["vision_ocr"] = {
            "status": "success",
            "engine": engine.engine_mode,
            "model": engine.vision_model_id,
            "latency_sec": round(t_vision, 2),
            "doctor": parsed.get("doctorName", ""),
            "patient": parsed.get("patientName", ""),
            "date": parsed.get("dateIssued", ""),
            "diagnosis": parsed.get("diagnosis", ""),
            "medications_count": len(parsed.get("medications", [])),
            "medications": parsed.get("medications", []),
            "unreadable_fields": parsed.get("unreadable_fields", []),
            "needs_review": parsed.get("needs_review", True)
        }
    except PrescriptionOCRError as e:
        results["vision_ocr"] = {
            "status": "failed",
            "error": str(e),
            "status_code": e.status_code,
            "latency_sec": round(time.time() - t_vision_start, 2)
        }
    except Exception as e:
        results["vision_ocr"] = {
            "status": "failed",
            "error": str(e),
            "latency_sec": round(time.time() - t_vision_start, 2)
        }

    return results

def main():
    parser = argparse.ArgumentParser(description="Evaluate Active Prescription OCR Pipeline")
    parser.add_argument("--image", type=str, help="Path to prescription image to evaluate")
    parser.add_argument("--benchmark", action="store_true", help="Generate and evaluate synthetic benchmark image")
    parser.add_argument("--output", type=str, help="Optional path to write JSON evaluation results")
    args = parser.parse_args()

    image_path = args.image
    if not image_path or not os.path.exists(image_path):
        if args.benchmark or not image_path:
            import tempfile
            sample_path = os.path.join(tempfile.gettempdir(), "prescription_benchmark_sample.png")
            create_synthetic_sample(sample_path)
            image_path = sample_path
            print(f"Created benchmark prescription sample at: {image_path}")

    is_valid, err = validate_image_file(image_path)
    if not is_valid:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Evaluating Prescription OCR on: {image_path}...")
    engine = PrescriptionOCREngine()
    report = evaluate_prescription(image_path, engine)
    
    print("\n### Evaluation Result:")
    print(json.dumps(report, indent=2))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved evaluation JSON to: {args.output}")

if __name__ == "__main__":
    main()
