import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
import joblib
import os

# ── Absolute paths ────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "eye_data.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

os.makedirs(MODEL_DIR, exist_ok=True)


def load_data():
    print(f"Loading data from: {DATA_FILE}")
    if not os.path.exists(DATA_FILE):
        print("No data file found! Run the app first.")
        return None

    df = pd.read_csv(DATA_FILE)
    for col in ["blink_rate", "face_width", "strain_score", "session_time"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna()
    print(f"Loaded {len(df)} valid rows")
    print(f"Users : {df['user_id'].value_counts().to_dict()}")
    return df


def label_data(df):
    def zoom_label(fw):
        if fw > 280:   return 2  # too close → zoom out
        elif fw < 150: return 1  # too far   → zoom in
        else:          return 0  # normal

    df = df.copy()
    df["zoom_action"] = df["face_width"].apply(zoom_label)
    print(f"\nZoom labels: {df['zoom_action'].value_counts().to_dict()}")
    print(f"  0 = no zoom  : {(df['zoom_action']==0).sum()} rows")
    print(f"  1 = zoom in  : {(df['zoom_action']==1).sum()} rows")
    print(f"  2 = zoom out : {(df['zoom_action']==2).sum()} rows")
    return df


def train():
    print("=" * 45)
    print("  EyeGuard ML Training — Zoom + Blink")
    print("=" * 45)

    df = load_data()
    if df is None:
        return

    if len(df) < 30:
        print(f"Only {len(df)} rows — need at least 30.")
        return

    df = label_data(df)

    # Features: blink_rate + face_width only (simple and effective)
    features = ["blink_rate", "face_width"]
    X = df[features]
    y = df["zoom_action"]

    # ── Train zoom model ──────────────────────────────────────────────────────
    print("\n--- Training Zoom Model ---")

    zoom_model = RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",   # handles imbalance (few zoom-out rows)
        random_state=42
    )

    # 5-fold cross-validation = real honest accuracy
    cv_scores = cross_val_score(zoom_model, X, y, cv=5, scoring="accuracy")
    print(f"  Cross-val accuracy : {cv_scores.mean()*100:.1f}% "
          f"(+/- {cv_scores.std()*100:.1f}%)")

    # Fit on ALL data for the saved model
    zoom_model.fit(X, y)

    # ── Feature importance ────────────────────────────────────────────────────
    print("\n--- Feature Importance ---")
    for feat, imp in sorted(zip(features, zoom_model.feature_importances_),
                             key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"  {feat:<15} {bar} {imp:.3f}")

    # ── Save zoom model only ──────────────────────────────────────────────────
    zoom_path = os.path.join(MODEL_DIR, "model_zoom.pkl")
    joblib.dump(zoom_model, zoom_path)

    print("\n" + "=" * 45)
    print(f"  Zoom model saved to: {zoom_path}")
    print(f"  Cross-val accuracy : {cv_scores.mean()*100:.1f}%")
    print("=" * 45)
    print("\nRestart main.py — zoom ML will be active!")


def load_models():
    zoom_path = os.path.join(MODEL_DIR, "model_zoom.pkl")
    try:
        zoom_model = joblib.load(zoom_path)
        print("Zoom ML model loaded!")
        return zoom_model
    except Exception:
        print("No zoom model found — using rule-based logic.")
        return None


def predict(zoom_model, blink_rate, face_width):
    """Returns zoom_action: 0=none, 1=zoom in, 2=zoom out"""
    try:
        features = [[blink_rate, face_width]]
        return zoom_model.predict(features)[0]
    except Exception:
        return 0


if __name__ == "__main__":
    train()