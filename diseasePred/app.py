import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import requests
# -------------------------------------------------
# 0️⃣ Streamlit Page Config
# -------------------------------------------------
st.set_page_config(page_title="LifeAura AI Disease Predictor", page_icon="🩺", layout="wide")

# -------------------------------------------------
# 1️⃣ Load Model and Metadata
# -------------------------------------------------

MODEL_URL = "https://drive.google.com/uc?export=download&id=1-YAyGCBT1q8W7wgieA_k7XB8NcUXlQgT"
MODEL_PATH = "disease_prediction_catboost_hybrid.pkl"

def load_model():
    # If not already downloaded, fetch from Google Drive
    if not os.path.exists(MODEL_PATH):
        with st.spinner("⬇️ Downloading model... please wait"):
            r = requests.get(MODEL_URL)
            with open(MODEL_PATH, "wb") as f:
                f.write(r.content)
            st.success("Model downloaded successfully!")

    # Load the pickle data
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)

    return data["model"], data["label_encoder"], data["symptoms"], data["accuracy"]

model, label_encoder, symptoms, accuracy = load_model()

# -------------------------------------------------
# 2️⃣ Load Disease Info and Doctor Mapping
# -------------------------------------------------
@st.cache_data
def load_disease_info():
    df = pd.read_csv("disease_list_with_counts.csv")
    df.columns = [col.strip() for col in df.columns]

    # Define severity based on disease type
    df["Severity"] = np.where(
        df["Disease"].str.lower().isin(
            ["heart attack", "stroke", "cancer", "kidney failure", "liver cirrhosis", "covid-19", "pneumonia"]
        ), "Severe",
        np.where(
            df["Disease"].str.lower().isin(
                ["diabetes", "hypertension", "asthma", "arthritis", "tuberculosis", "depression"]
            ), "Moderate", "Mild"
        )
    )

    # ---------------- Doctor Mapping ----------------
    mapping = {
        # 🧠 Neurology & Psychiatry
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

        # ❤️ Cardiology
        'heart attack': 'Cardiologist',
        'heart failure': 'Cardiologist',
        'hypertensive heart disease': 'Cardiologist',
        'angina': 'Cardiologist',
        'sinus bradycardia': 'Cardiologist',

        # 💨 Pulmonology
        'asthma': 'Pulmonologist',
        'chronic obstructive pulmonary disease (copd)': 'Pulmonologist',
        'acute bronchitis': 'Pulmonologist',
        'acute bronchiolitis': 'Pulmonologist',
        'pneumonia': 'Pulmonologist',
        'acute bronchospasm': 'Pulmonologist',
        'obstructive sleep apnea (osa)': 'Pulmonologist',
        'croup': 'Pulmonologist',

        # 🧬 Hematology
        'sickle cell crisis': 'Hematologist',
        'sepsis': 'Infectious Disease Specialist',
        'hypoglycemia': 'Endocrinologist',

        # 🧠 ENT (Ear, Nose, Throat)
        'otitis media': 'ENT Specialist',
        'otitis externa (swimmer\'s ear)': 'ENT Specialist',
        'ear drum damage': 'ENT Specialist',
        'eustachian tube dysfunction (ear disorder)': 'ENT Specialist',
        'nose disorder': 'ENT Specialist',
        'acute sinusitis': 'ENT Specialist',
        'seasonal allergies (hay fever)': 'ENT Specialist',
        'strep throat': 'ENT Specialist',

        # 👁 Ophthalmology
        'cornea infection': 'Ophthalmologist',
        'conjunctivitis': 'Ophthalmologist',
        'conjunctivitis due to allergy': 'Ophthalmologist',
        'blepharitis': 'Ophthalmologist',
        'stye': 'Ophthalmologist',
        'macular degeneration': 'Ophthalmologist',

        # 🦷 Dentistry
        'dental caries': 'Dentist',

        # 🦵 Orthopedics
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

        # 🩸 Gastroenterology
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

        # 🧫 Infectious Disease
        'fungal infection of the hair': 'Dermatologist',
        'pyogenic skin infection': 'Dermatologist',
        'drug reaction': 'Dermatologist',
        'allergy': 'Allergist',
        'contact dermatitis': 'Dermatologist',

        # 🧍‍♀️ Gynecology & Obstetrics
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

        # 🚻 Urology
        'urinary tract infection': 'Urologist',
        'pyelonephritis': 'Urologist',
        'cystitis': 'Urologist',
        'benign prostatic hyperplasia (bph)': 'Urologist',
        'kidney stone': 'Urologist',
        'acute kidney injury': 'Nephrologist',

        # 🩺 General/Internal Medicine
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

    # Apply doctor mapping
    df["Specialist"] = df["Disease"].str.lower().map(mapping).fillna("General Physician")

    return df

disease_info = load_disease_info()

# -------------------------------------------------
# 3️⃣ Streamlit UI
# -------------------------------------------------
st.title("LifeAura AI Disease Predictor")
st.markdown("---")

st.header("🧬 Select Your Symptoms")

# User selects symptoms
selected_symptoms = st.multiselect(
    "Select the symptoms you are experiencing:",
    options=symptoms,
    help="Choose multiple symptoms that best describe your condition."
)

# -------------------------------------------------
# 4️⃣ Prediction Logic
# -------------------------------------------------
if st.button("🔍 Predict Disease"):
    if not selected_symptoms:
        st.warning("⚠️ Please select at least one symptom.")
    else:
        # Create input vector
        input_vector = [1 if symptom in selected_symptoms else 0 for symptom in symptoms]
        X_input = np.array(input_vector).reshape(1, -1)

        # Predict probabilities
        probs = model.predict_proba(X_input)[0]
        diseases = label_encoder.inverse_transform(np.arange(len(probs)))

        # Top 3 predictions
        top_idx = np.argsort(probs)[::-1][:3]
        top_results = [(diseases[i], probs[i]) for i in top_idx]

        st.markdown("---")
        st.subheader("🏥 Top 3 Predicted Diseases")

        results_table = []
        for disease, prob in top_results:
            prob_percent = prob * 100
            info_row = disease_info[disease_info["Disease"].str.lower() == disease.lower()]

            specialist = info_row["Specialist"].values[0] if not info_row.empty else "General Physician"
            severity = info_row["Severity"].values[0] if not info_row.empty else "Mild"

            if severity == "Severe":
                st.error(f"⚠️ **{disease}** — {prob_percent:.2f}% | 👨‍⚕️ *{specialist}* | 🔴 *{severity}*")
            elif severity == "Moderate":
                st.warning(f"🟠 **{disease}** — {prob_percent:.2f}% | 👨‍⚕️ *{specialist}* | 🟡 *{severity}*")
            else:
                st.success(f"🟢 **{disease}** — {prob_percent:.2f}% | 👨‍⚕️ *{specialist}* | 🟢 *{severity}*")

            results_table.append((disease, prob_percent, specialist, severity))

        df_results = pd.DataFrame(results_table, columns=["Disease", "Probability (%)", "Specialist", "Severity"])
        st.dataframe(df_results, use_container_width=True)

        # st.markdown("### 📊 Probability Comparison")
        # st.bar_chart(df_results.set_index("Disease")["Probability (%)"])


# -------------------------------------------------
# 5️⃣ Footer
# -------------------------------------------------
st.markdown(
    """
    <hr>
    <div style='text-align:center; color:grey; font-size:13px;'>
    </div>
    """,
    unsafe_allow_html=True
)
