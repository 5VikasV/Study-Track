from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#B87542", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name")
    @classmethod
    def tidy_name(cls, value: str) -> str:
        return " ".join(value.split())


class SubjectOut(SubjectIn):
    id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class SessionIn(BaseModel):
    subject_id: int
    started_at: datetime
    duration_minutes: int = Field(ge=10, le=1440)
    mood: int = Field(ge=1, le=5)
    productivity: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=1000)


class SessionOut(SessionIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AdvisorIn(BaseModel):
    mood: int = Field(ge=1, le=5)
    available_minutes: int = Field(ge=15, le=720)


class ExamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject_id: int
    exam_date: date
    total_modules: int = Field(ge=1, le=250)
    daily_minutes: int = Field(ge=30, le=720)


class ExamOut(ExamIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    id: int
    exam_id: int
    subject_id: int
    title: str
    scheduled_for: date
    phase: str
    position: int
    completed: bool
    model_config = ConfigDict(from_attributes=True)
