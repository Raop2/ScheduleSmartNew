from datetime import datetime, timedelta
from typing import List, Dict
from app.backend.models import Task, UserPreferences

class GreedyScheduler:
    def schedule(self, tasks: List[Task], preferences: UserPreferences) -> Dict:
        # Sort by Deadline (Urgency) first, then Priority
        # This aligns with the "Greedy" approach defined in your methodology
        sorted_tasks = sorted(tasks, key=lambda t: (t.deadline if t.deadline else datetime.max, t.priority))

        # specific start time based on user preference
        current_day = datetime.now().date()
        if datetime.now().hour >= preferences.end_time_hour:
            current_day += timedelta(days=1)

        schedule_start = datetime.combine(current_day, datetime.min.time()).replace(hour=preferences.start_time_hour)

        occupied_slots = []
        scheduled_tasks = []
        unscheduled_tasks = []

        for task in sorted_tasks:
            if task.fixed_slot:
                # Handle tasks that must happen at a specific time
                scheduled_tasks.append({
                    "task_id": task.id,
                    "name": task.name,
                    "start_time": task.fixed_slot,
                    "end_time": task.fixed_slot + timedelta(minutes=task.duration_minutes),
                    "reason": "Fixed commitment defined by user."
                })
                occupied_slots.append((task.fixed_slot, task.fixed_slot + timedelta(minutes=task.duration_minutes)))
                continue

            # Search for the earliest free slot
            placed = False
            search_time = schedule_start

            # Limit search horizon to 14 days to prevent infinite loops
            days_searched = 0
            while not placed and days_searched < 14:
                # Check if current search time is within allowed daily hours
                if search_time.hour >= preferences.end_time_hour:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    days_searched += 1
                    continue

                # specific user preference: Skip weekends if requested
                if not preferences.include_weekends and search_time.weekday() >= 5:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    continue

                # Define the potential slot
                potential_end = search_time + timedelta(minutes=task.duration_minutes)

                # Check for overlap with existing tasks
                is_conflict = False
                for start, end in occupied_slots:
                    if not (potential_end <= start or search_time >= end):
                        is_conflict = True
                        # Jump to the end of the conflicting task to save time
                        search_time = end
                        break

                if is_conflict:
                    continue

                # Check if slot fits before the daily end time
                if potential_end.hour > preferences.end_time_hour:
                    search_time += timedelta(days=1)
                    search_time = search_time.replace(hour=preferences.start_time_hour, minute=0)
                    continue

                # Check if slot is before the task deadline
                if task.deadline and potential_end > task.deadline:
                    unscheduled_tasks.append({
                        "task_id": task.id,
                        "reason": f"Could not find time before deadline {task.deadline}"
                    })
                    placed = True
                    break

                # If we get here, the slot is valid
                scheduled_tasks.append({
                    "task_id": task.id,
                    "name": task.name,
                    "start_time": search_time,
                    "end_time": potential_end,
                    "reason": "Earliest available slot that fits your preferences."
                })
                occupied_slots.append((search_time, potential_end))
                placed = True

            if not placed and task.id not in [t["task_id"] for t in unscheduled_tasks]:
                unscheduled_tasks.append({"task_id": task.id, "reason": "No suitable slot found within 2 weeks."})

        return {
            "scheduled": sorted(scheduled_tasks, key=lambda x: x["start_time"]),
            "unscheduled": unscheduled_tasks,
            "status": "completed"
        }