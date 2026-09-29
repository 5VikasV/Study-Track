import os
from uuid import uuid4
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test-studytrack.db"
os.environ["SEED_DEMO_DATA"] = "false"
from fastapi.testclient import TestClient
from app.main import app


def test_health_and_session_flow():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        subject = client.post("/api/subjects", json={"name": f"Testing {uuid4()}", "color": "#6677A8"})
        assert subject.status_code == 201
        entry = client.post("/api/sessions", json={"subject_id": subject.json()["id"], "started_at": "2026-01-10T10:00:00", "duration_minutes": 60, "mood": 4, "productivity": 4})
        assert entry.status_code == 201
        assert client.get("/api/dashboard").json()["sample_count"] >= 1
        exam = client.post("/api/exams", json={"name": "Integration exam", "subject_id": subject.json()["id"], "exam_date": str(date.today() + timedelta(days=14)), "total_modules": 4, "daily_minutes": 90})
        assert exam.status_code == 201
        plan = client.get("/api/planner").json()
        assert any(item["exam_id"] == exam.json()["id"] for item in plan["exams"])
        task = next(item for item in plan["tasks"] if item["exam_id"] == exam.json()["id"])
        assert client.patch(f"/api/planner/tasks/{task['id']}").status_code == 200
