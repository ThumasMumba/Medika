# -*- coding: utf-8 -*-
"""
train.py
========
Reads the Kaggle dataset from data/ and trains a simple classifier.
Run this ONCE before anything else:

    python train.py

What it needs in data/:
    dataset.csv              - Disease, Symptom_1 ... Symptom_17
    symptom_Description.csv  - Disease, Description
    symptom_precaution.csv   - Disease, Precaution_1..4
    symptom_severity.csv     - Symptom, weight

What it saves to models/:
    model.pkl        - the trained TF-IDF + classifier pipeline
    disease_info.json - descriptions and precautions per disease
"""

import os, json, joblib, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

BASE  = os.path.dirname(os.path.abspath(__file__))
DATA  = os.path.join(BASE, "data")
MDL   = os.path.join(BASE, "models")
os.makedirs(MDL, exist_ok=True)

def read(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n  Missing: {path}"
            f"\n  Download the 4 CSVs from kaggle.com/datasets/itachi9604/"
            f"disease-symptom-description-dataset and place them in data/"
        )
    try:    return pd.read_csv(path, encoding="utf-8")
    except: return pd.read_csv(path, encoding="latin-1")

print("\n========================================")
print("  MEDIKA — Training the AI model")
print("========================================\n")

# ── 1. Load dataset.csv ───────────────────────────────────────────────────────
print("Step 1/4  Loading dataset.csv ...")
df = read("dataset.csv")

disease_col  = [c for c in df.columns if c.lower().strip() == "disease"][0]
symptom_cols = [c for c in df.columns if c.lower().strip().startswith("symptom")]

def join_symptoms(row):
    parts = []
    for col in symptom_cols:
        v = str(row[col]).strip()
        if v.lower() not in ("nan","none",""):
            parts.append(v.replace("_"," ").lower())
    return " ".join(parts)

df["text"]    = df.apply(join_symptoms, axis=1)
df["disease"] = df[disease_col].str.strip()
df = df[df["text"].str.len() > 0].reset_index(drop=True)

print(f"          {len(df)} rows, {df['disease'].nunique()} diseases\n")

# ── 2. Load descriptions and precautions ─────────────────────────────────────
print("Step 2/4  Loading descriptions and precautions ...")
desc_df = read("symptom_Description.csv")
prec_df = read("symptom_precaution.csv")

info = {}
for _, r in desc_df.iterrows():
    info[str(r.iloc[0]).strip()] = {
        "description": str(r.iloc[1]).strip() if len(r) > 1 else "",
        "precautions": []
    }
for _, r in prec_df.iterrows():
    name  = str(r.iloc[0]).strip()
    precs = [str(r.iloc[i]).strip() for i in range(1, len(r))
             if str(r.iloc[i]).strip().lower() not in ("nan","none","")]
    if name in info:
        info[name]["precautions"] = precs
    else:
        info[name] = {"description":"","precautions": precs}

with open(os.path.join(MDL,"disease_info.json"),"w",encoding="utf-8") as f:
    json.dump(info, f, indent=2, ensure_ascii=False)
print(f"          Saved disease_info.json for {len(info)} diseases\n")

# ── 3. Train the model ────────────────────────────────────────────────────────
print("Step 3/4  Training classifier ...")
X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["disease"], test_size=0.2, random_state=42, stratify=df["disease"]
)

pipe = Pipeline([
    # TF-IDF: turns symptom text into numbers the model can learn from.
    # ngram_range=(1,2) means it considers both single words ("fever") and
    # two-word phrases ("skin rash") as features.
    ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=8000, sublinear_tf=True)),
    # Logistic Regression: simple, fast, very accurate on this dataset (usually 95%+)
    ("clf",   LogisticRegression(max_iter=1000, C=5.0, solver="lbfgs",
                                  multi_class="multinomial", random_state=42))
])

pipe.fit(X_train, y_train)
acc = accuracy_score(y_test, pipe.predict(X_test))
print(f"          Accuracy on test set: {acc:.2%}\n")

# ── 4. Save model ─────────────────────────────────────────────────────────────
print("Step 4/4  Saving model ...")
joblib.dump(pipe, os.path.join(MDL,"model.pkl"))
with open(os.path.join(MDL,"meta.json"),"w") as f:
    json.dump({"accuracy": round(acc,4), "n_diseases": df['disease'].nunique()}, f)

print("          Saved model.pkl and meta.json\n")
print("========================================")
print(f"  Done! Accuracy: {acc:.2%}  |  Diseases: {df['disease'].nunique()}")
print("  Next: python test_cli.py")
print("========================================\n")
