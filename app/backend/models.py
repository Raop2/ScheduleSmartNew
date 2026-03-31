from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TaskPriority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TaskInput(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    module: str = Field("")
    duration: int = Field(..., gt=0)
    deadline: Optional[str] = Field(None)
    priority: TaskPriority = Field(TaskPriority.MEDIUM)
    preferred_time: str = Field("Any")
    is_fixed: bool = Field(False)
    start_time: Optional[str] = Field(None)
    end_time: Optional[str] = Field(None)
    notes: str = Field("")


class ScheduleRequest(BaseModel):
    tasks: List[TaskInput]
    strategy: str = Field("greedy", pattern="^(greedy|cpsat)$")
    start_date: str = Field(...)
    days_to_schedule: int = Field(7, ge=1, le=14)
    day_start: int = Field(8, ge=0, le=23)
    day_end: int = Field(22, ge=0, le=23)
    max_hours: int = Field(6, ge=1, le=12)
    break_mins: int = Field(15, ge=0, le=60)


class ScheduleResponse(BaseModel):
    scheduled_tasks: List[dict]
    unscheduled_tasks: List[dict]
    total_hours: float
    status: str
    quality_score: int