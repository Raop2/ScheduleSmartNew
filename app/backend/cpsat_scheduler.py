from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from app.backend.explanation import build_cpsat_reason

def get_slot_index(target_time, base_date, day_start):
    day_offset = (target_time.date() - base_date).days
    minutes_from_start = (target_time.hour - day_start) * 60 + target_time.minute
    return int((day_offset * 24 * 60 + minutes_from_start) / 30)

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

            start_slot = get_slot_index(st, start_date, day_start)
            duration_slots = max(1, int(((et - st).total_seconds() / 60) / 30))

            interval = model.NewFixedSizeIntervalVar(start_slot, duration_slots, f"fixed_{ft['id']}")
            intervals.append(interval)

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

        for d in range(days_to_schedule):
            day_start_slot = d * slots_per_day
            day_end_slot = day_start_slot + slots_per_day

            is_in_day = model.NewBoolVar(f"in_day_{d}_{flex['id']}")

            model.Add(start_var >= day_start_slot).OnlyEnforceIf(is_in_day)
            model.Add(end_var <= day_end_slot).OnlyEnforceIf(is_in_day)

            model.Add(start_var < day_start_slot).OnlyEnforceIf(is_in_day.Not())

    model.AddNoOverlap(intervals)

    penalty_terms = []
    for tid, var_dict in task_vars.items():
        flex = var_dict['task']
        start_var = var_dict['start']

        if flex.get('priority') == 'High':
            penalty_terms.append(start_var * 2)

        pref_start_hr, pref_end_hr = parse_time_window_slots(flex.get('preferred_time', 'Any'), day_start, day_end)

        if flex.get('preferred_time') and flex.get('preferred_time') != 'Any':
            ideal_start_slot_relative = (pref_start_hr - day_start) * 2

            day_index = model.NewIntVar(0, days_to_schedule - 1, f"day_idx_{tid}")
            model.AddDivisionEquality(day_index, start_var, slots_per_day)

            slot_within_day = model.NewIntVar(0, slots_per_day, f"slot_within_{tid}")
            model.AddModuloEquality(slot_within_day, start_var, slots_per_day)

            deviation = model.NewIntVar(0, total_slots, f"dev_{tid}")
            model.AddAbsEquality(deviation, slot_within_day - ideal_start_slot_relative)
            penalty_terms.append(deviation * 5)

    if penalty_terms:
        model.Minimize(sum(penalty_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 4

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

            was_preferred = flex.get('preferred_time') != 'Any' and status == cp_model.OPTIMAL
            task_ref['explanation'] = build_cpsat_reason(task_ref, str(actual_date), str(dt_start.time()), was_preferred)

    return fixed_tasks + flexible_tasks