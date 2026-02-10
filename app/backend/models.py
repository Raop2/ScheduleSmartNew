from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Task(BaseModel):
    id: str = Field(...)
    name: str = Field(...)
    duration_minutes: int = Field(..., gt=0)
    deadline: Optional[datetime] = Field(None)
    priority: TaskPriority = Field(TaskPriority.MEDIUM)
    fixed_slot: Optional[datetime] = Field(None)

class UserPreferences(BaseModel):
    start_time_hour: int = Field(9, ge=0, le=23)
    end_time_hour: int = Field(17, ge=0, le=23)
    include_weekends: bool = Field(False)

class ScheduleRequest(BaseModel):
    tasks: List[Task]
    preferences: UserPreferences

class ScheduleResponse(BaseModel):
    scheduled_tasks: List[dict]
    unscheduled_tasks: List[dict]
    total_hours: float
    status: str