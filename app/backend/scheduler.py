from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.backend.models import Task, UserPreferences, TaskPriority
from ortools.sat.python import cp_model

class ScheduleEngine:
    def generate_schedule(self, tasks: List[Task], prefs: UserPreferences, method: str = "cpsat") -> Dict[str, Any]:
        """
        Main entry point. Routes to the correct solver.
        """
        if not tasks:
            return {"scheduled": [], "unscheduled": [], "status": "empty"}

        # Simply route everything to CP-SAT for now as it's the smartest
        return self._solve_cpsat(tasks, prefs)

    def _solve_cpsat(self, tasks: List[Task], prefs: UserPreferences):
        model = cp_model.CpModel()

        # 1. Variables
        # We map each task to an Interval Variable
        task_intervals = {}
        task_starts = {}
        task_ends = {}

        # Calculate day limits in minutes (e.g., 9:00 = 540)
        day_start_min = prefs.start_time_hour * 60
        day_end_min = prefs.end_time_hour * 60
        day_length = day_end_min - day_start_min

        # Horizon: How far ahead do we look? (e.g., 5 days)
        horizon_days = 5
        horizon_min = horizon_days * 24 * 60

        for t in tasks:
            # Start time variable (0 to Horizon)
            start_var = model.NewIntVar(0, horizon_min, f"start_{t.id}")
            end_var = model.NewIntVar(0, horizon_min, f"end_{t.id}")

            # Interval variable (enforces start + duration = end)
            interval_var = model.NewIntervalVar(
                start_var, t.duration_minutes, end_var, f"interval_{t.id}"
            )

            task_intervals[t.id] = interval_var
            task_starts[t.id] = start_var
            task_ends[t.id] = end_var

        # 2. Constraint: No Overlap
        model.AddNoOverlap(task_intervals.values())

        # 3. Constraint: Work Hours Only (Simplified)
        # Force tasks to start after day_start and end before day_end (modulo arithmetic logic is complex in CP-SAT)
        # For this prototype, we will just use a simple linear timeline and assume user works continuously
        # or we treat "Time 0" as "Start of Day 1".

        # 4. Objective: Minimize Lateness & Maximize Priority
        # (Simplified: Just schedule everything as early as possible)
        makespan = model.NewIntVar(0, horizon_min, 'makespan')
        model.AddMaxEquality(makespan, list(task_ends.values()))
        model.Minimize(makespan)

        # 5. Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        scheduled_tasks = []

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            base_date = datetime.now().date()
            base_time = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=prefs.start_time_hour)

            for t in tasks:
                start_val = solver.Value(task_starts[t.id])

                # Convert "minutes from start" to real datetime
                # (This is a simplified logic: assuming continuous time for the demo)
                real_start = base_time + timedelta(minutes=start_val)
                real_end = real_start + timedelta(minutes=t.duration_minutes)

                scheduled_tasks.append({
                    "id": t.id,  # <--- CRITICAL: RETURN THE ID!
                    "name": t.name,
                    "start_time": real_start,
                    "end_time": real_end,
                    "priority": t.priority.value if hasattr(t.priority, 'value') else "medium",
                    "reason": "Optimized by AI"
                })

            return {
                "scheduled": scheduled_tasks,
                "unscheduled": [],
                "status": "success"
            }
        else:
            return {
                "scheduled": [],
                "unscheduled": tasks,
                "status": "failed"
            }