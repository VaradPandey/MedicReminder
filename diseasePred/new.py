
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_selection import VarianceThreshold
from sklearn.metrics import accuracy_score
from catboost import CatBoostClassifier

# -------------------------------
# 1. Load dataset
# -------------------------------
df = pd.read_csv("Disease and symptoms dataset.csv")

# -------------------------------
# 2. Filter diseases with ≥900 samples (adaptive selection)
# -------------------------------
counts = df['diseases'].value_counts()
df_filtered = df[df['diseases'].isin(counts[counts >= 900].index)]
print(f"✅ Using {df_filtered['diseases'].nunique()} diseases (each ≥900 samples)")

# -------------------------------
# 3. Balance dataset (max 900 rows per disease)
# -------------------------------
balanced_df = (
    df_filtered.groupby('diseases', group_keys=False)
    .apply(lambda x: x.sample(n=min(len(x), 900), random_state=42))
    .reset_index(drop=True)
)
print(f"✅ Balanced dataset shape: {balanced_df.shape}")

# -------------------------------
# 4. Features and labels
# -------------------------------
X = balanced_df.drop('diseases', axis=1).fillna(0)
y = balanced_df['diseases']

# -------------------------------
# 5. Remove near-constant features
# -------------------------------
selector = VarianceThreshold(threshold=0.001)
X_reduced = selector.fit_transform(X)
reduced_features = X.columns[selector.get_support()].tolist()
print(f"✅ Features reduced from {X.shape[1]} → {len(reduced_features)}")

# -------------------------------
# 6. Encode labels
# -------------------------------
le = LabelEncoder()
y_enc = le.fit_transform(y)

# -------------------------------
# 7. Train-test split (stratified)
# -------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X_reduced, y_enc, test_size=0.2, stratify=y_enc, random_state=42
)

# -------------------------------
# 8. Identify categorical features (if any)
# -------------------------------
cat_features = [
    i for i, c in enumerate(reduced_features)
    if balanced_df[c].dtype == 'object'
]
print(f"✅ Categorical feature indices: {cat_features}")

# -------------------------------
# 9. Train CatBoost (hybrid-tuned)
# -------------------------------
model = CatBoostClassifier(
    iterations=1100,
    learning_rate=0.05,
    depth=7,
    l2_leaf_reg=3,
    border_count=254,
    random_strength=0.7,
    colsample_bylevel=0.9,
    subsample=0.85,
    bootstrap_type='Bernoulli',
    eval_metric='Accuracy',
    auto_class_weights='Balanced',
    random_seed=42,
    verbose=150,
    early_stopping_rounds=80
)

model.fit(X_train, y_train, cat_features=cat_features, eval_set=(X_test, y_test))

# -------------------------------
# 10. Evaluate accuracy
# -------------------------------
pred = model.predict(X_test)
acc = accuracy_score(y_test, pred)
print(f"\n✅ Final Test Accuracy: {acc:.4f}")

# -------------------------------
# 11. Save model and metadata
# -------------------------------
with open("disease_prediction_catboost_hybrid.pkl", "wb") as f:
    pickle.dump({
        "model": model,
        "label_encoder": le,
        "symptoms": reduced_features,
        "accuracy": acc
    }, f)

print("💾 Model saved to disease_prediction_catboost_hybrid.pkl")

# -------------------------------
# 12. Save disease counts (for Streamlit app)
# -------------------------------
disease_counts = balanced_df['diseases'].value_counts().reset_index()
disease_counts.columns = ['Disease', 'Sample_Count']
disease_counts.to_csv("disease_list_with_counts.csv", index=False)
print("📄 Disease list saved as disease_list_with_counts.csv")

