from datetime import datetime


def format_slot(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%A at %H:%M")
    except (ValueError, TypeError):
        return "Unplaced"


def build_greedy_reason(task, placement_time, was_preferred_window):
    reason_parts = []
    day_name = placement_time.strftime("%A")
    time_str = placement_time.strftime("%H:%M")

    if task.get('priority') == 'High':
        reason_parts.append(f"high priority task scheduled early on {day_name} at {time_str}")
    else:
        reason_parts.append(f"{task.get('priority', 'Medium').lower()} priority task placed on {day_name} at {time_str}")

    if task.get('deadline'):
        reason_parts.append(f"deadline of {task['deadline']} factored into sorting order")

    if was_preferred_window:
        reason_parts.append(f"fitted into your preferred '{task.get('preferred_time', 'Any')}' window")
    else:
        reason_parts.append("preferred window was full so the next available slot was used")

    return "; ".join(reason_parts).capitalize() + "."


def build_cpsat_reason(task, day_str, time_str, was_preferred):
    reason_parts = []

    try:
        day_name = datetime.fromisoformat(day_str).strftime("%A")
    except (ValueError, TypeError):
        day_name = day_str

    if task.get('priority') == 'High':
        reason_parts.append(f"high priority task placed on {day_name} at {time_str}")
    else:
        reason_parts.append(f"placed on {day_name} at {time_str} to balance workload across the week")

    if was_preferred:
        reason_parts.append(f"your '{task.get('preferred_time', 'Any')}' preference was respected")
    else:
        reason_parts.append("shifted outside your preferred window to keep daily hours even")

    reason_parts.append("daily maximum hour limit respected")

    return "; ".join(reason_parts).capitalize() + "."


def compare_explanations(greedy_task, cpsat_task):
    g_start = greedy_task.get('start_time')
    c_start = cpsat_task.get('start_time')

    g_label = format_slot(g_start) if g_start else "Unplaced"
    c_label = format_slot(c_start) if c_start else "Unplaced"

    if not g_start and not c_start:
        return "Neither engine found a valid slot for this task."

    if not c_start:
        return f"Greedy placed it on **{g_label}**, but CP-SAT could not fit it without violating balancing or hour limits."

    if not g_start:
        return f"Greedy ran out of space, but CP-SAT reshuffled other tasks and placed it on **{c_label}**."

    if g_start == c_start:
        return f"Both engines agreed on the same slot: **{g_label}**."

    return f"Greedy chose **{g_label}** (first available). CP-SAT chose **{c_label}** (optimised for weekly balance)."


def generate_schedule_summary(scheduled_tasks, total_input_tasks):
    placed = len([t for t in scheduled_tasks if t.get('start_time')])
    unplaced = total_input_tasks - placed

    total_minutes = sum(t.get('duration', 0) for t in scheduled_tasks if t.get('start_time'))
    total_hours = round(total_minutes / 60, 1)

    return {
        "placed": placed,
        "unplaced": unplaced,
        "total_hours": total_hours,
        "success_rate": round((placed / total_input_tasks) * 100) if total_input_tasks > 0 else 0
    }