import uvicorn
from fastapi import FastAPI
from app.backend.models import ScheduleRequest, ScheduleResponse
from app.backend.scheduler import ScheduleEngine

app = FastAPI(title="ScheduleSmart", version="1.0.0")

@app.get("/")
def health_check():
    return {"status": "online", "system": "ScheduleSmart"}

@app.post("/schedule", response_model=ScheduleResponse)
def generate_schedule(request: ScheduleRequest):
    engine = ScheduleEngine()

    # Dynamic Strategy Selection (Greedy vs CP-SAT)
    result = engine.generate_schedule(
        request.tasks,
        request.preferences,
        method=request.strategy
    )

    total_minutes = sum([t.duration_minutes for t in request.tasks])

    return ScheduleResponse(
        scheduled_tasks=result["scheduled"],
        unscheduled_tasks=result["unscheduled"],
        total_hours=total_minutes / 60.0,
        status=result["status"]
    )

if __name__ == "__main__":
    uvicorn.run("app.backend.main:app", host="127.0.0.1", port=8000, reload=True)