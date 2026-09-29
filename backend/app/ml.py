import json
from pathlib import Path
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

MODEL_PATH = Path(__file__).parent.parent / "studytrack-model.joblib"
MIN_MODEL_SESSIONS = 12


def train(joined_rows):
    rows = list(joined_rows)
    if len(rows) < MIN_MODEL_SESSIONS or len({subject.id for _, subject in rows}) < 2:
        return None
    subject_ids = sorted({subject.id for _, subject in rows})
    index = {id_: n for n, id_ in enumerate(subject_ids)}
    x = [[session.duration_minutes, session.mood, index[subject.id]] for session, subject in rows]
    y = [session.productivity for session, _ in rows]
    model = RandomForestRegressor(n_estimators=120, max_depth=5, random_state=42)
    model.fit(x, y)
    mae = mean_absolute_error(y, model.predict(x))
    payload = {"model": model, "subject_index": index, "sample_count": len(rows), "mae": round(float(mae), 2)}
    joblib.dump(payload, MODEL_PATH)
    return {"sample_count": len(rows), "mae": payload["mae"]}


def predict(duration_minutes, mood, subject_id):
    if not MODEL_PATH.exists():
        return None
    payload = joblib.load(MODEL_PATH)
    index = payload["subject_index"]
    encoded = index.get(subject_id, sum(index.values()) / len(index))
    value = float(payload["model"].predict([[duration_minutes, mood, encoded]])[0])
    confidence = max(0, min(100, round((1 - payload["mae"] / 4) * 100)))
    return {"score": round(max(1, min(5, value)), 1), "confidence": confidence, "sample_count": payload["sample_count"]}
