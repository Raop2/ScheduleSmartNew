"""
cpsat_scheduler.py — CP-SAT Constraint Solver Engine
Uses Google OR-Tools to model the entire week as a constraint satisfaction
problem and find the globally optimal schedule. Balances workload across days,
respects priorities and time preferences. Implements FR-03.
"""
import math
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from app.backend.explanation import build_cpsat_reason

def get_slot_index(target_time, base_date, day_start, day_end):
    day_offset = (target_time.date() - base_date).days
    slots_per_day = (day_end - day_start) * 2
    minutes_from_day_start = (target_time.hour - day_start) * 60 + target_time.minute
    slot_in_day = int(minutes_from_day_start / 30)
    return day_offset * slots_per_day + slot_in_day

def get_end_slot_index(target_time, base_date, day_start, day_end):
    day_offset = (target_time.date() - base_date).days
    slots_per_day = (day_end - day_start) * 2
    minutes_from_day_start = (target_time.hour - day_start) * 60 + target_time.minute
    slot_in_day = math.ceil(minutes_from_day_start / 30)
    return day_offset * slots_per_day + slot_in_day

def parse_time_window_slots(preferred_time, day_start, day_end):
    windows = {
        "Morning": (max(day_start, 8), min(day_end, 12)),
        "Afternoon": (max(day_start, 12), min(day_end, 17)),
        "Evening": (max(day_start, 17), min(day_end, 22))
    }
    return windows.get(preferred_time, (day_start, day_end))

def generate_cpsat_schedule(tasks, start_date, days_to_schedule, day_start, day_end, max_hours, break_mins):
    model = cp_model.CpModel()

    slots_per_day = (day_end - day_start) * 2
    total_slots = days_to_schedule * slots_per_day
    max_slots_per_day = int((max_hours * 60) / 30)

    task_vars = {}
    intervals = []

    fixed_tasks = [t for t in tasks if t.get('is_fixed')]
    flexible_tasks = [t for t in tasks if not t.get('is_fixed')]

    for ft in fixed_tasks:
        if ft.get('start_time') and ft.get('end_time'):
            st = datetime.fromisoformat(ft['start_time'])
            et = datetime.fromisoformat(ft['end_time'])

            start_slot = get_slot_index(st, start_date, day_start, day_end)
            end_slot = get_end_slot_index(et, start_date, day_start, day_end)
            duration_slots = max(1, end_slot - start_slot)

            if 0 <= start_slot < total_slots:
                clamped_duration = min(duration_slots, total_slots - start_slot)
                interval = model.NewFixedSizeIntervalVar(start_slot, clamped_duration, f"fixed_{ft['id']}")
                intervals.append(interval)

    daily_loads = {d: [] for d in range(days_to_schedule)}

    for flex in flexible_tasks:
        duration_slots = max(1, int(flex.get('duration', 60) / 30))

        start_var = model.NewIntVar(0, total_slots - duration_slots, f"start_{flex['id']}")
        end_var = model.NewIntVar(0, total_slots, f"end_{flex['id']}")

        interval = model.NewIntervalVar(start_var, duration_slots, end_var, f"interval_{flex['id']}")
        intervals.append(interval)

        task_vars[flex['id']] = {
            'start': start_var,
            'end': end_var,
            'duration': duration_slots,
            'task': flex
        }

        # STRICT DAY LOCK FOR HABITS
        is_habit = flex.get('notes') == 'AI Generated Habit'
        target_date_str = flex.get('deadline')

        if is_habit and target_date_str:
            try:
                target_date_obj = datetime.fromisoformat(target_date_str).date()
                target_d = (target_date_obj - start_date).days
                if 0 <= target_d < days_to_schedule:
                    target_start_slot = target_d * slots_per_day
                    target_end_slot = target_start_slot + slots_per_day
                    model.Add(start_var >= target_start_slot)
                    model.Add(end_var <= target_end_slot)
            except ValueError:
                pass

                # PROPER DAY LOGIC (FIXES THE 0 PLACED BUG)
        day_assigned = model.NewIntVar(0, days_to_schedule - 1, f"day_assign_{flex['id']}")
        model.AddDivisionEquality(day_assigned, start_var, slots_per_day)

        for d in range(days_to_schedule):
            is_in_day = model.NewBoolVar(f"in_day_{d}_{flex['id']}")
            model.Add(day_assigned == d).OnlyEnforceIf(is_in_day)
            model.Add(day_assigned != d).OnlyEnforceIf(is_in_day.Not())

            task_load_in_day = model.NewIntVar(0, duration_slots, f"load_{d}_{flex['id']}")
            model.Add(task_load_in_day == duration_slots).OnlyEnforceIf(is_in_day)
            model.Add(task_load_in_day == 0).OnlyEnforceIf(is_in_day.Not())
            daily_loads[d].append(task_load_in_day)

    model.AddNoOverlap(intervals)
    penalty_terms = []

    # GLOBAL LOAD BALANCING PENALTY (This is what makes CP-SAT superior to Greedy!)
    if daily_loads:
        daily_sum_vars = []
        for d in range(days_to_schedule):
            day_sum = model.NewIntVar(0, max_slots_per_day, f"day_sum_{d}")
            if daily_loads[d]:
                model.Add(day_sum == sum(daily_loads[d]))
            else:
                model.Add(day_sum == 0)
            daily_sum_vars.append(day_sum)

        max_daily_load = model.NewIntVar(0, max_slots_per_day, "max_daily_load")
        model.AddMaxEquality(max_daily_load, daily_sum_vars)
        penalty_terms.append(max_daily_load * 20)

    for tid, var_dict in task_vars.items():
        flex = var_dict['task']
        start_var = var_dict['start']

        if flex.get('priority') == 'High':
            penalty_terms.append(start_var * 1)

        pref_start_hr, pref_end_hr = parse_time_window_slots(flex.get('preferred_time', 'Any'), day_start, day_end)

        if flex.get('preferred_time') and flex.get('preferred_time') != 'Any':
            ideal_start_slot_relative = (pref_start_hr - day_start) * 2

            slot_within_day = model.NewIntVar(0, slots_per_day, f"slot_within_{tid}")
            model.AddModuloEquality(slot_within_day, start_var, slots_per_day)

            diff_var = model.NewIntVar(-slots_per_day, slots_per_day, f"diff_{tid}")
            model.Add(diff_var == slot_within_day - ideal_start_slot_relative)

            deviation = model.NewIntVar(0, slots_per_day, f"dev_{tid}")
            model.AddAbsEquality(deviation, diff_var)
            penalty_terms.append(deviation * 5)

    if penalty_terms:
        model.Minimize(sum(penalty_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0

    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for tid, var_dict in task_vars.items():
            start_val = solver.Value(var_dict['start'])

            day_offset = int(start_val / slots_per_day)
            slot_remainder = start_val % slots_per_day

            actual_date = start_date + timedelta(days=day_offset)
            actual_hour = day_start + int(slot_remainder / 2)
            actual_minute = 30 if slot_remainder % 2 != 0 else 0

            dt_start = datetime.combine(actual_date, datetime.min.time()).replace(hour=actual_hour, minute=actual_minute)
            dt_end = dt_start + timedelta(minutes=var_dict['duration'] * 30)

            task_ref = var_dict['task']
            task_ref['start_time'] = dt_start.isoformat()
            task_ref['end_time'] = dt_end.isoformat()

            was_preferred = var_dict['task'].get('preferred_time') != 'Any' and status == cp_model.OPTIMAL
            task_ref['explanation'] = build_cpsat_reason(task_ref, str(actual_date), str(dt_start.time()), was_preferred)

    return fixed_tasks + flexible_tasks