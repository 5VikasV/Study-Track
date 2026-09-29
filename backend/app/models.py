from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(12), default="#B87542")
    active: Mapped[bool] = mapped_column(default=True)


class StudySession(Base):
    __tablename__ = "study_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    mood: Mapped[int] = mapped_column(Integer)
    productivity: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelSnapshot(Base):
    __tablename__ = "model_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    metrics_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=120)
    total_modules: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(index=True)
    subject_id: Mapped[int] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(140))
    scheduled_for: Mapped[date] = mapped_column(Date, index=True)
    phase: Mapped[str] = mapped_column(String(24))
    position: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
