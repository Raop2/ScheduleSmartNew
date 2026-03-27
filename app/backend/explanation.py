def build_greedy_reason(task, placement_time, was_preferred_window):
    reason_parts = []

    if task.get('priority') == 'High':
        reason_parts.append("High priority task prioritized early in the sequence")
    else:
        reason_parts.append(f"{task.get('priority', 'Medium')} priority task sequenced normally")

    if task.get('deadline'):
        reason_parts.append(f"deadline of {task['deadline']} factored into sorting")

    if was_preferred_window:
        reason_parts.append(f"successfully fitted into your preferred '{task.get('preferred_time', 'Any')}' window")
    else:
        reason_parts.append("placed in the first available slot outside preferred window due to constraints")

    return "; ".join(reason_parts).capitalize() + "."

def build_cpsat_reason(task, day_str, time_str, was_preferred):
    reason_parts = []

    if task.get('priority') == 'High':
        reason_parts.append("High priority constraint heavily weighted for earlier placement")

    if was_preferred:
        reason_parts.append(f"optimiser successfully minimized penalty for your '{task.get('preferred_time', 'Any')}' preference")
    else:
        reason_parts.append("optimiser accepted a time penalty to ensure overall workload balance across the week")

    reason_parts.append("daily maximum hour constraints respected")

    return "; ".join(reason_parts).capitalize() + "."

def compare_explanations(greedy_task, cpsat_task):
    g_start = greedy_task.get('start_time', 'Unplaced')
    c_start = cpsat_task.get('start_time', 'Unplaced')

    if g_start == c_start:
        return "Both engines reached the exact same optimal slot for this task."

    if c_start == 'Unplaced':
        return "Greedy forced the task in, but CP-SAT determined it violates strict balancing or maximum hour constraints."

    if g_start == 'Unplaced':
        return "CP-SAT successfully reshuffled other tasks to make room, whereas Greedy ran out of sequential space."

    return "The engines chose different slots. CP-SAT optimized the entire week globally, while Greedy locked in the earliest chronological fit."

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