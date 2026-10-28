"""
MedicReminder Disease Predictor Module.
Loads CatBoost hybrid model and provides symptom-based disease predictions.
"""

import os
import pickle
import logging
import requests
import numpy as np
import pandas as pd

logger = logging.getLogger("ML][PREDICTOR")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "disease_prediction_catboost_hybrid.pkl")
CSV_PATH = os.path.join(BASE_DIR, "disease_list_with_counts.csv")
MODEL_URL = os.getenv(
    "MODEL_URL",
    "https://drive.usercontent.google.com/download?id=1-YAyGCBT1q8W7wgieA_k7XB8NcUXlQgT&export=download",
)

MODEL = None
LABEL_ENCODER = None
SYMPTOMS_LIST = None
ACCURACY = None
DISEASE_INFO = None
_IS_INITIALIZED = False


def init_predictor():
    """Initializes model and metadata."""
    global MODEL, LABEL_ENCODER, SYMPTOMS_LIST, ACCURACY, DISEASE_INFO, _IS_INITIALIZED

    if _IS_INITIALIZED:
        return True

    # 1. Download model if missing
    if not os.path.exists(MODEL_PATH):
        logger.info(f"Model artifact '{MODEL_PATH}' not found. Downloading from remote URL...")
        try:
            r = requests.get(MODEL_URL, timeout=120)
            r.raise_for_status()
            with open(MODEL_PATH, "wb") as f:
                f.write(r.content)
            logger.info(f"Successfully downloaded {MODEL_PATH} ({len(r.content)} bytes)")
        except Exception as e:
            logger.error(f"Failed to download model artifact: {e}")
            return False

    # 2. Load model pickle
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        MODEL = data["model"]
        LABEL_ENCODER = data["label_encoder"]
        SYMPTOMS_LIST = data["symptoms"]
        ACCURACY = data.get("accuracy", None)
    except Exception as e:
        logger.error(f"Failed to load model from {MODEL_PATH}: {e}")
        return False

    # 3. Load disease CSV info & mappings
    try:
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            df.columns = [c.strip() for c in df.columns]

            df["Severity"] = np.where(
                df["Disease"].str.lower().isin(
                    ["heart attack", "stroke", "cancer", "kidney failure", "liver cirrhosis", "covid-19", "pneumonia"]
                ),
                "Severe",
                np.where(
                    df["Disease"].str.lower().isin(
                        ["diabetes", "hypertension", "asthma", "arthritis", "tuberculosis", "depression"]
                    ),
                    "Moderate",
                    "Mild",
                ),
            )

            mapping = {
                'multiple sclerosis': 'Neurologist',
                'neurosis': 'Psychiatrist',
                'psychotic disorder': 'Psychiatrist',
                'personality disorder': 'Psychiatrist',
                'panic disorder': 'Psychiatrist',
                'acute stress reaction': 'Psychiatrist',
                'anxiety': 'Psychiatrist',
                'complex regional pain syndrome': 'Neurologist',
                'peripheral nerve disorder': 'Neurologist',
                'concussion': 'Neurologist',
                'developmental disability': 'Neurologist',
                'heart attack': 'Cardiologist',
                'heart failure': 'Cardiologist',
                'hypertensive heart disease': 'Cardiologist',
                'angina': 'Cardiologist',
                'sinus bradycardia': 'Cardiologist',
                'asthma': 'Pulmonologist',
                'chronic obstructive pulmonary disease (copd)': 'Pulmonologist',
                'acute bronchitis': 'Pulmonologist',
                'acute bronchiolitis': 'Pulmonologist',
                'pneumonia': 'Pulmonologist',
                'acute bronchospasm': 'Pulmonologist',
                'obstructive sleep apnea (osa)': 'Pulmonologist',
                'croup': 'Pulmonologist',
                'sickle cell crisis': 'Hematologist',
                'sepsis': 'Infectious Disease Specialist',
                'hypoglycemia': 'Endocrinologist',
                'otitis media': 'ENT Specialist',
                "otitis externa (swimmer's ear)": 'ENT Specialist',
                'ear drum damage': 'ENT Specialist',
                'eustachian tube dysfunction (ear disorder)': 'ENT Specialist',
                'nose disorder': 'ENT Specialist',
                'acute sinusitis': 'ENT Specialist',
                'seasonal allergies (hay fever)': 'ENT Specialist',
                'strep throat': 'ENT Specialist',
                'cornea infection': 'Ophthalmologist',
                'conjunctivitis': 'Ophthalmologist',
                'conjunctivitis due to allergy': 'Ophthalmologist',
                'blepharitis': 'Ophthalmologist',
                'stye': 'Ophthalmologist',
                'macular degeneration': 'Ophthalmologist',
                'dental caries': 'Dentist',
                'injury to the leg': 'Orthopedic Surgeon',
                'injury to the arm': 'Orthopedic Surgeon',
                'injury to the trunk': 'Orthopedic Surgeon',
                'sprain or strain': 'Orthopedic Surgeon',
                'degenerative disc disease': 'Orthopedic Surgeon',
                'spondylosis': 'Orthopedic Surgeon',
                'spinal stenosis': 'Orthopedic Surgeon',
                'herniated disk': 'Orthopedic Surgeon',
                'arthritis of the hip': 'Orthopedic Surgeon',
                'bursitis': 'Orthopedic Surgeon',
                'appendicitis': 'Gastroenterologist',
                'diverticulitis': 'Gastroenterologist',
                'noninfectious gastroenteritis': 'Gastroenterologist',
                'infectious gastroenteritis': 'Gastroenterologist',
                'gastrointestinal hemorrhage': 'Gastroenterologist',
                'esophagitis': 'Gastroenterologist',
                'hiatal hernia': 'Gastroenterologist',
                'cholecystitis': 'Gastroenterologist',
                'gallstone': 'Gastroenterologist',
                'liver disease': 'Hepatologist',
                'rectal disorder': 'Gastroenterologist',
                'fungal infection of the hair': 'Dermatologist',
                'pyogenic skin infection': 'Dermatologist',
                'drug reaction': 'Dermatologist',
                'allergy': 'Allergist',
                'contact dermatitis': 'Dermatologist',
                'vaginitis': 'Gynecologist',
                'vaginal cyst': 'Gynecologist',
                'hyperemesis gravidarum': 'Gynecologist',
                'problem during pregnancy': 'Gynecologist',
                'threatened pregnancy': 'Gynecologist',
                'spontaneous abortion': 'Gynecologist',
                'idiopathic painful menstruation': 'Gynecologist',
                'idiopathic irregular menstrual cycle': 'Gynecologist',
                'idiopathic excessive menstruation': 'Gynecologist',
                'vulvodynia': 'Gynecologist',
                'urinary tract infection': 'Urologist',
                'pyelonephritis': 'Urologist',
                'cystitis': 'Urologist',
                'benign prostatic hyperplasia (bph)': 'Urologist',
                'kidney stone': 'Urologist',
                'acute kidney injury': 'Nephrologist',
                'common cold': 'General Physician',
                'pain after an operation': 'General Physician',
                'marijuana abuse': 'General Physician',
                'chronic constipation': 'Gastroenterologist',
                'psoriasis': 'Dermatologist',
                'eczema': 'Dermatologist',
                'sebaceous cyst': 'Dermatologist',
                'skin pigmentation disorder': 'Dermatologist',
                'actinic keratosis': 'Dermatologist'
            }
            df["Specialist"] = df["Disease"].str.lower().map(mapping).fillna("General Physician")
            DISEASE_INFO = df
    except Exception as e:
        logger.warning(f"Could not load disease metadata CSV: {e}")

    _IS_INITIALIZED = True
    logger.info("Disease Predictor successfully initialized.")
    return True


def get_symptoms():
    """Returns list of all available symptoms."""
    if not _IS_INITIALIZED:
        init_predictor()
    if not SYMPTOMS_LIST:
        return {"error": "Symptoms list not loaded"}, 500
    return {"symptoms": SYMPTOMS_LIST, "accuracy": ACCURACY}, 200


def predict(symptoms):
    """Predicts diseases based on input symptoms list."""
    if not _IS_INITIALIZED:
        init_predictor()
    if MODEL is None or LABEL_ENCODER is None:
        return {"error": "Disease model not loaded"}, 500
    if not symptoms or not isinstance(symptoms, list):
        return {"error": "symptoms must be a non-empty list"}, 400

    input_vector = [1 if s in symptoms else 0 for s in SYMPTOMS_LIST]
    X_input = np.array(input_vector).reshape(1, -1)

    probs = MODEL.predict_proba(X_input)[0]
    diseases = LABEL_ENCODER.inverse_transform(np.arange(len(probs)))

    top_idx = np.argsort(probs)[::-1][:3]
    top_results = []
    for i in top_idx:
        disease = diseases[i]
        prob = float(probs[i])
        specialist = "General Physician"
        severity = "Mild"
        if DISEASE_INFO is not None and not DISEASE_INFO.empty:
            info_row = DISEASE_INFO[DISEASE_INFO["Disease"].str.lower() == disease.lower()]
            if not info_row.empty:
                specialist = info_row["Specialist"].values[0]
                severity = info_row["Severity"].values[0]
        top_results.append({
            "disease": disease,
            "probability": prob,
            "specialist": specialist,
            "severity": severity,
        })

    return {"predictions": top_results, "accuracy": ACCURACY}, 200
