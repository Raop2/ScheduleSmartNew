from datetime import datetime, timedelta
from typing import List, Dict
from ortools.sat.python import cp_model
from app.backend.models import Task, UserPreferences

class ScheduleEngine:
    def generate_schedule(self, tasks: List[Task], preferences: UserPreferences, method: str = "greedy") -> Dict:
        if method == "cpsat":
            return CPSATScheduler().schedule(tasks, preferences)
        return GreedyScheduler().schedule(tasks, preferences)

class GreedyScheduler:
    def schedule(self, tasks: List[Task], preferences: UserPreferences) -> Dict:
        sorted_tasks = sorted(tasks, key=lambda t: (t.deadline if t.deadline else datetime.max, t.priority))

        current_day = datetime.now().date()
        if datetime.now().hour >= preferences.end_time_hour:
            current_day += timedelta(days=1)

        schedule_start = datetime.combine(current_day, datetime.min.time()).replace(hour=preferences.start_time_hour)

        occupied_slots = []
        scheduled_tasks = []
        unscheduled_tasks = []

        for task in sorted_tasks:
            if task.fixed_slot:
                scheduled_tasks.append({
                    "task_id": task.id,
                    "name": task.name,
                    "start_time": task.fixed_slot,
                    "end_time": task.fixed_slot + timedelta(minutes=task.duration_minutes),
                    "reason": "Fixed commitment defined by user."
                })
                occupied_slots.append((task.fixed_slot, task.fixed_slot + timedelta(minutes=task.duration_minutes)))
                continue

            placed = False
            search_time = schedule_start
            days_searched = 0

            while not placed and days_searched < 14:
                if search_time.hour >= preferences.end_time_hour:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    days_searched += 1
                    continue

                if not preferences.include_weekends and search_time.weekday() >= 5:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    continue

                potential_end = search_time + timedelta(minutes=task.duration_minutes)

                is_conflict = False
                for start, end in occupied_slots:
                    if not (potential_end <= start or search_time >= end):
                        is_conflict = True
                        search_time = end
                        break

                if is_conflict:
                    continue

                if potential_end.hour > preferences.end_time_hour:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    continue

                if task.deadline and potential_end > task.deadline:
                    unscheduled_tasks.append({
                        "task_id": task.id,
                        "reason": f"Deadline constraint {task.deadline} exceeded."
                    })
                    placed = True
                    break

                scheduled_tasks.append({
                    "task_id": task.id,
                    "name": task.name,
                    "start_time": search_time,
                    "end_time": potential_end,
                    "reason": "Optimal slot found via Greedy Search."
                })
                occupied_slots.append((search_time, potential_end))
                placed = True

            if not placed and task.id not in [t["task_id"] for t in unscheduled_tasks]:
                unscheduled_tasks.append({"task_id": task.id, "reason": "No suitable slot found in search horizon."})

        return {
            "scheduled": sorted(scheduled_tasks, key=lambda x: x["start_time"]),
            "unscheduled": unscheduled_tasks,
            "status": "completed"
        }

class CPSATScheduler:
    def schedule(self, tasks: List[Task], preferences: UserPreferences) -> Dict:
        model = cp_model.CpModel()

        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        horizon_minutes = 14 * 24 * 60

        task_vars = {}
        intervals = []

        for task in tasks:
            start_var = model.NewIntVar(0, horizon_minutes, f'start_{task.id}')
            end_var = model.NewIntVar(0, horizon_minutes, f'end_{task.id}')
            interval_var = model.NewIntervalVar(start_var, task.duration_minutes, end_var, f'interval_{task.id}')

            task_vars[task.id] = {
                'start': start_var,
                'end': end_var,
                'interval': interval_var,
                'task': task
            }
            intervals.append(interval_var)

            if task.deadline:
                minutes_to_deadline = int((task.deadline - base_time).total_seconds() / 60)
                model.Add(end_var <= max(0, minutes_to_deadline))

            if task.fixed_slot:
                start_min = int((task.fixed_slot - base_time).total_seconds() / 60)
                model.Add(start_var == start_min)

        model.AddNoOverlap(intervals)

        if task_vars:
            makespan = model.NewIntVar(0, horizon_minutes, 'makespan')
            model.AddMaxEquality(makespan, [v['end'] for v in task_vars.values()])
            model.Minimize(makespan)

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        scheduled_tasks = []
        unscheduled_tasks = []

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for t_id, vars in task_vars.items():
                start_offset = solver.Value(vars['start'])
                actual_start_time = base_time + timedelta(minutes=start_offset)
                actual_end_time = actual_start_time + timedelta(minutes=vars['task'].duration_minutes)

                reason = "Calculated by CP-SAT solver for maximum efficiency."
                if not preferences.include_weekends and actual_start_time.weekday() >= 5:
                    reason += " Weekend included to meet tight deadline."

                scheduled_tasks.append({
                    "task_id": t_id,
                    "name": vars['task'].name,
                    "start_time": actual_start_time,
                    "end_time": actual_end_time,
                    "reason": reason
                })
        else:
            return {"scheduled": [], "unscheduled": [{"reason": "Model Infeasible"}], "status": "failed"}

        return {
            "scheduled": sorted(scheduled_tasks, key=lambda x: x["start_time"]),
            "unscheduled": unscheduled_tasks,
            "status": "optimized"
        }