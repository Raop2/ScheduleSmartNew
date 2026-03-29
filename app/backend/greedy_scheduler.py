from datetime import datetime, timedelta
from app.backend.explanation import build_greedy_reason

def parse_time_window(preferred_time, day_start, day_end):
    windows = {
        "Morning": (max(day_start, 8), min(day_end, 12)),
        "Afternoon": (max(day_start, 12), min(day_end, 17)),
        "Evening": (max(day_start, 17), min(day_end, 22))
    }
    return windows.get(preferred_time, (day_start, day_end))

def get_priority_weight(priority):
    weights = {"High": 1, "Medium": 2, "Low": 3}
    return weights.get(priority, 3)

def generate_greedy_schedule(tasks, start_date, days_to_schedule, day_start, day_end, max_hours, break_mins):
    fixed_tasks = [t for t in tasks if t.get('is_fixed')]
    flexible_tasks = [t for t in tasks if not t.get('is_fixed')]

    flexible_tasks.sort(key=lambda x: (
        x.get('deadline') or "9999-12-31",
        get_priority_weight(x.get('priority'))
    ))

    daily_booked_minutes = {i: 0 for i in range(days_to_schedule)}
    max_mins_per_day = max_hours * 60

    booked_slots = []
    for ft in fixed_tasks:
        if ft.get('start_time') and ft.get('end_time'):
            st = datetime.fromisoformat(ft['start_time'])
            et = datetime.fromisoformat(ft['end_time'])
            booked_slots.append((st, et))

    for task in flexible_tasks:
        duration = task.get('duration', 60)
        task_placed = False

        pref_start, pref_end = parse_time_window(task.get('preferred_time', 'Any'), day_start, day_end)

        is_habit = task.get('notes') == 'AI Generated Habit'
        target_date_str = task.get('deadline')

        for attempt in range(2):
            if task_placed: break

            for day_offset in range(days_to_schedule):
                if task_placed: break

                current_date = start_date + timedelta(days=day_offset)

                # STRICT DAY LOCK: If this is an AI Habit, it CANNOT be scheduled on the wrong day.
                if is_habit and target_date_str and current_date.isoformat() != target_date_str:
                    continue

                if daily_booked_minutes[day_offset] + duration > max_mins_per_day:
                    continue

                search_start_hour = pref_start if attempt == 0 else day_start
                search_end_hour = pref_end if attempt == 0 else day_end

                current_time = datetime.combine(current_date, datetime.min.time()).replace(hour=search_start_hour)
                end_of_search = datetime.combine(current_date, datetime.min.time()).replace(hour=search_end_hour)

                while current_time + timedelta(minutes=duration) <= end_of_search:
                    proposed_end = current_time + timedelta(minutes=duration)

                    overlap = False
                    for b_start, b_end in booked_slots:
                        if current_time < b_end and proposed_end > b_start:
                            overlap = True
                            current_time = b_end + timedelta(minutes=break_mins)
                            break

                    if not overlap:
                        task['start_time'] = current_time.isoformat()
                        task['end_time'] = proposed_end.isoformat()
                        task['explanation'] = build_greedy_reason(task, current_time, attempt == 0)

                        booked_slots.append((current_time, proposed_end))
                        daily_booked_minutes[day_offset] += duration
                        task_placed = True
                        break

    return fixed_tasks + flexible_tasks