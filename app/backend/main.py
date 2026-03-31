import sys
from pathlib import Path
from datetime import date

root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

import uvicorn
from fastapi import FastAPI
from app.backend.models import ScheduleRequest, ScheduleResponse, TaskInput
from app.backend.greedy_scheduler import generate_greedy_schedule
from app.backend.cpsat_scheduler import generate_cpsat_schedule
from app.backend.explanation import generate_schedule_summary

app = FastAPI(
    title="ScheduleSmart API",
    version="2.0.0",
    description="Intelligent study scheduling API with greedy and CP-SAT engines"
)


@app.get("/")
def health_check():
    return {"status": "online", "system": "ScheduleSmart", "version": "2.0.0"}


@app.get("/health")
def detailed_health():
    return {
        "status": "online",
        "engines": ["greedy", "cpsat"],
        "version": "2.0.0"
    }


def convert_tasks_to_dicts(tasks: list[TaskInput]) -> list[dict]:
    return [
        {
            "id": t.id,
            "name": t.name,
            "module": t.module,
            "duration": t.duration,
            "deadline": t.deadline,
            "priority": t.priority.value,
            "preferred_time": t.preferred_time,
            "is_fixed": t.is_fixed,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "notes": t.notes,
        }
        for t in tasks
    ]


def calculate_api_quality_score(scheduled_tasks, days):
    placed = [t for t in scheduled_tasks if t.get('start_time') and not t.get('is_fixed')]
    if not placed:
        return 0

    from datetime import datetime
    score = 100
    daily_hours = {}
    for t in placed:
        try:
            day = datetime.fromisoformat(t['start_time']).date().isoformat()
            daily_hours[day] = daily_hours.get(day, 0) + t.get('duration', 0) / 60
        except (ValueError, TypeError):
            pass

    if len(daily_hours) > 1:
        hours_list = list(daily_hours.values())
        spread = max(hours_list) - min(hours_list)
        score -= min(30, int(spread * 8))

    return max(0, min(100, score))


@app.post("/schedule", response_model=ScheduleResponse)
def generate_schedule(request: ScheduleRequest):
    task_dicts = convert_tasks_to_dicts(request.tasks)
    start = date.fromisoformat(request.start_date)

    if request.strategy == "greedy":
        result = generate_greedy_schedule(
            task_dicts, start, request.days_to_schedule,
            request.day_start, request.day_end,
            request.max_hours, request.break_mins
        )
    else:
        result = generate_cpsat_schedule(
            task_dicts, start, request.days_to_schedule,
            request.day_start, request.day_end,
            request.max_hours, request.break_mins
        )

    scheduled = [t for t in result if t.get('start_time')]
    unscheduled = [t for t in result if not t.get('start_time') and not t.get('is_fixed')]
    total_minutes = sum(t.get('duration', 0) for t in scheduled)
    quality = calculate_api_quality_score(result, request.days_to_schedule)

    return ScheduleResponse(
        scheduled_tasks=scheduled,
        unscheduled_tasks=unscheduled,
        total_hours=round(total_minutes / 60, 1),
        status="success" if scheduled else "failed",
        quality_score=quality
    )


if __name__ == "__main__":
    uvicorn.run("app.backend.main:app", host="127.0.0.1", port=8000, reload=True)