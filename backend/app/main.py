import json
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from .analytics import analyze
from .database import Base, engine, get_db
from .models import Exam, ModelSnapshot, PlanTask, StudySession, Subject
from .schemas import AdvisorIn, ExamIn, ExamOut, SessionIn, SessionOut, SubjectIn, SubjectOut, TaskOut
from . import ml
from .planner import build_tasks, feasibility, priority

app = FastAPI(title="StudyTrack API", version="1.0.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

PALETTE = ["#B87542", "#617A57", "#6677A8", "#B05A62"]
SEED = [("Mathematics", "#B87542"), ("Physics", "#617A57"), ("Algorithms", "#6677A8")]


def joined(db):
    return db.execute(select(StudySession, Subject).join(Subject, StudySession.subject_id == Subject.id).order_by(StudySession.started_at)).all()


def retrain(db):
    result = ml.train(joined(db))
    if result:
        db.add(ModelSnapshot(sample_count=result["sample_count"], metrics_json=json.dumps(result)))
        db.commit()
    return result


def seed(db):
    if db.scalar(select(StudySession.id).limit(1)):
        return
    subjects = []
    for name, color in SEED:
        s = Subject(name=name, color=color)
        db.add(s); subjects.append(s)
    db.flush()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    values = [(0, 75, 4, 4), (1, 100, 3, 3), (2, 90, 5, 5), (0, 120, 4, 4), (1, 60, 2, 2), (2, 110, 4, 4),
              (0, 95, 5, 5), (1, 140, 3, 3), (2, 70, 4, 4), (0, 80, 3, 4), (1, 90, 4, 4), (2, 105, 5, 5),
              (0, 150, 2, 2), (1, 75, 4, 4), (2, 85, 3, 3)]
    for day, (subject_i, mins, mood, prod) in enumerate(values):
        db.add(StudySession(subject_id=subjects[subject_i].id, started_at=now-timedelta(days=15-day), duration_minutes=mins, mood=mood, productivity=prod))
    db.commit(); retrain(db)
    # Seed two plans so the planner is demonstrable on first launch.
    maths = db.scalar(select(Subject).where(Subject.name == "Mathematics"))
    physics = db.scalar(select(Subject).where(Subject.name == "Physics"))
    db.add_all([Exam(name="Mathematics Midterm", subject_id=maths.id, exam_date=(now + timedelta(days=17)).date(), total_modules=12, daily_minutes=120),
                Exam(name="Physics Assessment", subject_id=physics.id, exam_date=(now + timedelta(days=25)).date(), total_modules=10, daily_minutes=90)])
    db.commit(); regenerate_plan(db)


def exam_rows(db):
    return db.execute(select(Exam, Subject).join(Subject, Exam.subject_id == Subject.id).order_by(Exam.exam_date)).all()


def regenerate_plan(db):
    rows = exam_rows(db)
    done = {}
    for task in db.scalars(select(PlanTask).where(PlanTask.completed.is_(True))):
        done[task.exam_id] = done.get(task.exam_id, 0) + 1
    db.execute(delete(PlanTask).where(PlanTask.completed.is_(False)))
    for task in build_tasks(rows, done): db.add(PlanTask(**task))
    db.commit()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    if os.getenv("SEED_DEMO_DATA", "true").lower() == "true":
        with Session(bind=engine) as db: seed(db)


@app.get("/api/health")
def health(): return {"status": "ok"}


@app.get("/api/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db)):
    return db.scalars(select(Subject).where(Subject.active.is_(True)).order_by(Subject.name)).all()


@app.post("/api/subjects", response_model=SubjectOut, status_code=201)
def create_subject(data: SubjectIn, db: Session = Depends(get_db)):
    if db.scalar(select(Subject).where(Subject.name.ilike(data.name))):
        raise HTTPException(409, "A subject with that name already exists.")
    subject = Subject(name=data.name, color=data.color or PALETTE[0]); db.add(subject); db.commit(); db.refresh(subject)
    return subject


@app.get("/api/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return db.scalars(select(StudySession).order_by(StudySession.started_at.desc())).all()


@app.post("/api/sessions", response_model=SessionOut, status_code=201)
def create_session(data: SessionIn, db: Session = Depends(get_db)):
    if not db.get(Subject, data.subject_id): raise HTTPException(404, "Subject not found.")
    session = StudySession(**data.model_dump()); db.add(session); db.commit(); db.refresh(session); retrain(db); return session


@app.put("/api/sessions/{session_id}", response_model=SessionOut)
def update_session(session_id: int, data: SessionIn, db: Session = Depends(get_db)):
    session = db.get(StudySession, session_id)
    if not session: raise HTTPException(404, "Session not found.")
    if not db.get(Subject, data.subject_id): raise HTTPException(404, "Subject not found.")
    for key, value in data.model_dump().items(): setattr(session, key, value)
    db.commit(); db.refresh(session); retrain(db); return session


@app.delete("/api/sessions/{session_id}", status_code=204)
def remove_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(StudySession, session_id)
    if not session: raise HTTPException(404, "Session not found.")
    db.delete(session); db.commit(); retrain(db)


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    report = analyze(joined(db))
    cards = feasibility(exam_rows(db), db.scalars(select(PlanTask)).all())
    report["upcoming_exams"] = cards[:3]
    report["today_target"] = len(db.scalars(select(PlanTask).where(PlanTask.scheduled_for == datetime.now().date(), PlanTask.completed.is_(False))).all())
    return report


@app.get("/api/insights")
def advanced_insights(db: Session = Depends(get_db)):
    rows = joined(db); report = analyze(rows); sessions = [session for session, _ in rows]
    if len(sessions) < 4:
        return {**report, "cognitive": None, "progress": []}
    recent, earlier = sessions[-min(5, len(sessions)):], sessions[:max(1, len(sessions)//2)]
    recent_avg = sum(s.productivity for s in recent) / len(recent)
    early_avg = sum(s.productivity for s in earlier) / len(earlier)
    values = [s.productivity for s in sessions]
    variance = sum((v - sum(values)/len(values)) ** 2 for v in values) / len(values)
    cognitive = {"recent_average": round(recent_avg, 1), "baseline_average": round(early_avg, 1),
                 "stability": round(max(0, 100 - variance * 18)),
                 "burnout_risk": "watch" if recent_avg < early_avg - .7 else "low",
                 "focus_efficiency": round(sum(s.productivity / max(1, s.duration_minutes) * 60 for s in sessions) / len(sessions), 2)}
    progress = []
    for stat in report["subject_stats"]:
        named = [s for s, subject in rows if subject.name == stat["subject"]]
        if len(named) > 1:
            split = max(1, len(named)//2)
            progress.append({"subject": stat["subject"], "first_half": round(sum(s.productivity for s in named[:split])/split, 1),
                             "recent_half": round(sum(s.productivity for s in named[split:])/len(named[split:]), 1)})
    return {**report, "cognitive": cognitive, "progress": progress}


@app.get("/api/replay")
def replay(db: Session = Depends(get_db)):
    rows = joined(db); events = []
    last_subject = None; switches = 0
    for session, subject in rows:
        switched = last_subject is not None and last_subject != subject.name
        switches += int(switched); last_subject = subject.name
        events.append({"id": session.id, "date": session.started_at.isoformat(), "subject": subject.name,
                       "minutes": session.duration_minutes, "productivity": session.productivity, "mood": session.mood,
                       "switched_subject": switched})
    streak_days = len({event["date"][:10] for event in events})
    highlights = [{"title": "Study footprint", "body": f"{len(events)} sessions across {streak_days} study days."},
                  {"title": "Context switching", "body": f"{switches} subject switches observed. Group related work when you need deeper focus."}]
    if events: highlights.append({"title": "Latest session", "body": f"{events[-1]['subject']} scored {events[-1]['productivity']}/5."})
    return {"events": events, "highlights": highlights}


@app.get("/api/model-status")
def model_status(db: Session = Depends(get_db)):
    count = db.scalar(select(StudySession).count()) if False else len(joined(db))
    return {"ready": count >= ml.MIN_MODEL_SESSIONS and ml.MODEL_PATH.exists(), "sample_count": count, "minimum_samples": ml.MIN_MODEL_SESSIONS}


@app.post("/api/advisor")
def advisor(data: AdvisorIn, db: Session = Depends(get_db)):
    report = analyze(joined(db)); stats = report["subject_stats"]
    if not stats: raise HTTPException(422, "Log a study session before requesting advice.")
    target = stats[-1] if len(stats) > 1 and data.mood >= 4 else stats[0]
    duration = min(data.available_minutes, 90 if data.mood >= 4 else 50)
    breaks = "25 minutes focus / 5 minutes break" if duration <= 60 else "50 minutes focus / 10 minutes break"
    subject = db.scalar(select(Subject).where(Subject.name == target["subject"]))
    prediction = ml.predict(duration, data.mood, subject.id) if subject else None
    rationale = (f"{target['subject']} is your current growth opportunity; use this higher-energy window for it."
                 if target == stats[-1] and len(stats) > 1 else f"Start with {target['subject']}, where your recent performance is most reliable.")
    return {"subject": target["subject"], "duration_minutes": duration, "break_rhythm": breaks,
            "rationale": rationale, "prediction": prediction, "model_ready": prediction is not None}


@app.get("/api/exams", response_model=list[ExamOut])
def list_exams(db: Session = Depends(get_db)):
    return db.scalars(select(Exam).order_by(Exam.exam_date)).all()


@app.post("/api/exams", response_model=ExamOut, status_code=201)
def create_exam(data: ExamIn, db: Session = Depends(get_db)):
    if not db.get(Subject, data.subject_id): raise HTTPException(404, "Subject not found.")
    if data.exam_date <= datetime.now().date(): raise HTTPException(422, "Exam date must be in the future.")
    exam = Exam(**data.model_dump()); db.add(exam); db.commit(); db.refresh(exam); regenerate_plan(db); return exam


@app.delete("/api/exams/{exam_id}", status_code=204)
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam: raise HTTPException(404, "Exam not found.")
    db.execute(delete(PlanTask).where(PlanTask.exam_id == exam_id)); db.delete(exam); db.commit(); regenerate_plan(db)


@app.get("/api/planner")
def planner(db: Session = Depends(get_db)):
    rows = exam_rows(db); tasks = db.scalars(select(PlanTask).order_by(PlanTask.scheduled_for, PlanTask.position)).all()
    report = analyze(joined(db)); cards = feasibility(rows, tasks)
    return {"exams": cards, "tasks": [{"id": t.id, "exam_id": t.exam_id, "subject_id": t.subject_id, "title": t.title,
             "scheduled_for": t.scheduled_for.isoformat(), "phase": t.phase, "position": t.position, "completed": t.completed} for t in tasks],
            "priorities": priority(cards, report["subject_stats"]), "today": [t.id for t in tasks if t.scheduled_for == datetime.now().date() and not t.completed]}


@app.patch("/api/planner/tasks/{task_id}", response_model=TaskOut)
def complete_task(task_id: int, completed: bool = True, db: Session = Depends(get_db)):
    task = db.get(PlanTask, task_id)
    if not task: raise HTTPException(404, "Plan task not found.")
    task.completed = completed; task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if completed else None
    db.commit(); regenerate_plan(db); db.refresh(task); return task


@app.post("/api/demo/reset", status_code=204)
def reset_demo(db: Session = Depends(get_db)):
    db.execute(delete(PlanTask)); db.execute(delete(Exam)); db.execute(delete(StudySession)); db.execute(delete(ModelSnapshot)); db.execute(delete(Subject)); db.commit()
    if ml.MODEL_PATH.exists(): ml.MODEL_PATH.unlink()
    seed(db)
