from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import numpy as np
import pandas as pd
import pickle

app = FastAPI(title="CURE-BOT Disease Prediction API")


class PredictRequest(BaseModel):
    symptoms: List[str]


@app.on_event("startup")
def load_resources():
    global MODEL, LABEL_ENCODER, SYMPTOMS_LIST, DISEASE_INFO, ACCURACY
    with open("disease_prediction_catboost_hybrid.pkl", "rb") as f:
        data = pickle.load(f)
    MODEL = data["model"]
    LABEL_ENCODER = data["label_encoder"]
    SYMPTOMS_LIST = data["symptoms"]
    ACCURACY = data.get("accuracy", None)

    # load disease info for metadata
    df = pd.read_csv("disease_list_with_counts.csv")
    df.columns = [c.strip() for c in df.columns]

    # compute Severity and Specialist mapping (keep same logic as Streamlit app)
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


@app.post("/predict")
def predict(req: PredictRequest):
    if not req.symptoms:
        raise HTTPException(status_code=400, detail="symptoms must be a non-empty list")

    # build input vector
    input_vector = [1 if s in req.symptoms else 0 for s in SYMPTOMS_LIST]
    X_input = np.array(input_vector).reshape(1, -1)

    probs = MODEL.predict_proba(X_input)[0]
    diseases = LABEL_ENCODER.inverse_transform(np.arange(len(probs)))

    top_idx = np.argsort(probs)[::-1][:3]
    top_results = []
    for i in top_idx:
        disease = diseases[i]
        prob = float(probs[i])
        info_row = DISEASE_INFO[DISEASE_INFO["Disease"].str.lower() == disease.lower()]
        specialist = info_row["Specialist"].values[0] if not info_row.empty else "General Physician"
        severity = info_row["Severity"].values[0] if not info_row.empty else "Mild"
        top_results.append({"disease": disease, "probability": prob, "specialist": specialist, "severity": severity})

    return {"predictions": top_results, "accuracy": ACCURACY}


@app.get("/symptoms")
def get_symptoms():
    # Return the symptoms list and model accuracy
    if not SYMPTOMS_LIST:
        raise HTTPException(status_code=500, detail="Symptoms not loaded")
    return {"symptoms": SYMPTOMS_LIST, "accuracy": ACCURACY}
