import sys
import unittest
from pathlib import Path
from datetime import datetime, date, timedelta

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

from app.backend.greedy_scheduler import generate_greedy_schedule, get_priority_weight, parse_time_window
from app.backend.cpsat_scheduler import generate_cpsat_schedule
from app.backend.explanation import build_greedy_reason, build_cpsat_reason, compare_explanations, generate_schedule_summary
from app.backend.motivator import get_greeting, get_hype_message, get_streak_message, get_recovery_message, get_focus_tip
from app.backend.export_service import generate_ics_file
from app.backend.partial_resolve import safe_parse_datetime, detect_all_overlaps, find_nearest_free_slot


class TestGreedyScheduler(unittest.TestCase):

    def setUp(self):
        self.start_date = date.today()
        self.simple_tasks = [
            {"id": "1", "name": "Maths Revision", "duration": 60, "priority": "High", "deadline": None,
             "preferred_time": "Morning", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""},
            {"id": "2", "name": "Physics Essay", "duration": 60, "priority": "Medium", "deadline": None,
             "preferred_time": "Afternoon", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""},
        ]

    def test_returns_all_tasks(self):
        result = generate_greedy_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        self.assertEqual(len(result), 2)

    def test_all_tasks_get_scheduled(self):
        result = generate_greedy_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        for task in result:
            self.assertIsNotNone(task.get('start_time'), f"Task {task['name']} was not scheduled")
            self.assertIsNotNone(task.get('end_time'), f"Task {task['name']} has no end time")

    def test_no_overlapping_tasks(self):
        result = generate_greedy_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        scheduled = [(datetime.fromisoformat(t['start_time']), datetime.fromisoformat(t['end_time'])) for t in result if t.get('start_time')]
        for i, (s1, e1) in enumerate(scheduled):
            for j, (s2, e2) in enumerate(scheduled):
                if i >= j:
                    continue
                self.assertFalse(s1 < e2 and s2 < e1, f"Tasks {i} and {j} overlap")

    def test_high_priority_scheduled_first(self):
        result = generate_greedy_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        high = next(t for t in result if t['priority'] == 'High')
        medium = next(t for t in result if t['priority'] == 'Medium')
        if high.get('start_time') and medium.get('start_time'):
            self.assertLessEqual(high['start_time'], medium['start_time'])

    def test_fixed_tasks_stay_in_place(self):
        tasks = [
            {"id": "f1", "name": "Lecture", "duration": 60, "priority": "High", "is_fixed": True,
             "start_time": datetime.combine(self.start_date, datetime.min.time()).replace(hour=10).isoformat(),
             "end_time": datetime.combine(self.start_date, datetime.min.time()).replace(hour=11).isoformat(),
             "preferred_time": "Any", "deadline": None, "notes": ""},
        ]
        result = generate_greedy_schedule(tasks, self.start_date, 7, 8, 22, 6, 15)
        fixed = next(t for t in result if t['id'] == 'f1')
        self.assertIn("10:00", fixed['start_time'])

    def test_respects_max_hours_per_day(self):
        many_tasks = [
            {"id": str(i), "name": f"Task {i}", "duration": 120, "priority": "Medium",
             "is_fixed": False, "start_time": None, "end_time": None, "preferred_time": "Any",
             "deadline": None, "notes": ""}
            for i in range(10)
        ]
        result = generate_greedy_schedule(many_tasks, self.start_date, 3, 8, 22, 4, 0)
        daily_minutes = {}
        for t in result:
            if t.get('start_time') and not t.get('is_fixed'):
                day = datetime.fromisoformat(t['start_time']).date().isoformat()
                daily_minutes[day] = daily_minutes.get(day, 0) + t['duration']
        for day, mins in daily_minutes.items():
            self.assertLessEqual(mins, 4 * 60, f"Day {day} exceeds max hours")

    def test_empty_task_list(self):
        result = generate_greedy_schedule([], self.start_date, 7, 8, 22, 6, 15)
        self.assertEqual(result, [])

    def test_explanations_are_generated(self):
        result = generate_greedy_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        for task in result:
            if not task.get('is_fixed') and task.get('start_time'):
                self.assertIn('explanation', task, f"Task {task['name']} has no explanation")
                self.assertTrue(len(task['explanation']) > 10)


class TestCPSATScheduler(unittest.TestCase):

    def setUp(self):
        self.start_date = date.today()
        self.simple_tasks = [
            {"id": "1", "name": "Maths", "duration": 60, "priority": "High", "deadline": None,
             "preferred_time": "Morning", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""},
            {"id": "2", "name": "Physics", "duration": 60, "priority": "Medium", "deadline": None,
             "preferred_time": "Afternoon", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""},
            {"id": "3", "name": "English", "duration": 60, "priority": "Low", "deadline": None,
             "preferred_time": "Any", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""},
        ]

    def test_returns_all_tasks(self):
        result = generate_cpsat_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        self.assertEqual(len(result), 3)

    def test_all_tasks_get_scheduled(self):
        result = generate_cpsat_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        for task in result:
            if not task.get('is_fixed'):
                self.assertIsNotNone(task.get('start_time'), f"Task {task['name']} was not scheduled")

    def test_no_overlapping_tasks(self):
        result = generate_cpsat_schedule(self.simple_tasks, self.start_date, 7, 8, 22, 6, 15)
        scheduled = [(datetime.fromisoformat(t['start_time']), datetime.fromisoformat(t['end_time'])) for t in result if t.get('start_time')]
        for i, (s1, e1) in enumerate(scheduled):
            for j, (s2, e2) in enumerate(scheduled):
                if i >= j:
                    continue
                self.assertFalse(s1 < e2 and s2 < e1, f"Tasks {i} and {j} overlap")

    def test_respects_fixed_tasks(self):
        tasks = [
            {"id": "f1", "name": "Lecture", "duration": 60, "priority": "High", "is_fixed": True,
             "start_time": datetime.combine(self.start_date, datetime.min.time()).replace(hour=10).isoformat(),
             "end_time": datetime.combine(self.start_date, datetime.min.time()).replace(hour=11).isoformat(),
             "preferred_time": "Any", "deadline": None, "notes": ""},
            {"id": "2", "name": "Study", "duration": 60, "priority": "Medium", "is_fixed": False,
             "start_time": None, "end_time": None, "preferred_time": "Any", "deadline": None, "notes": ""},
        ]
        result = generate_cpsat_schedule(tasks, self.start_date, 7, 8, 22, 6, 15)
        study = next(t for t in result if t['id'] == '2')
        if study.get('start_time'):
            s = datetime.fromisoformat(study['start_time'])
            e = datetime.fromisoformat(study['end_time'])
            lecture_s = datetime.combine(self.start_date, datetime.min.time()).replace(hour=10)
            lecture_e = datetime.combine(self.start_date, datetime.min.time()).replace(hour=11)
            overlaps = s < lecture_e and lecture_s < e
            self.assertFalse(overlaps, "Study task overlaps with fixed lecture")

    def test_empty_task_list(self):
        result = generate_cpsat_schedule([], self.start_date, 7, 8, 22, 6, 15)
        self.assertEqual(result, [])


class TestExplanationEngine(unittest.TestCase):

    def test_greedy_reason_contains_text(self):
        task = {"priority": "High", "deadline": "2026-04-10", "preferred_time": "Morning"}
        placement_time = datetime(2026, 4, 1, 9, 0)
        reason = build_greedy_reason(task, placement_time, True)
        self.assertIsInstance(reason, str)
        self.assertTrue(len(reason) > 10)
        self.assertTrue(reason.endswith("."))

    def test_greedy_reason_outside_preferred_window(self):
        task = {"priority": "Medium", "preferred_time": "Morning"}
        placement_time = datetime(2026, 4, 1, 14, 0)
        reason = build_greedy_reason(task, placement_time, False)
        self.assertIsInstance(reason, str)

    def test_compare_same_slots(self):
        g = {"start_time": "2026-04-01T09:00:00"}
        c = {"start_time": "2026-04-01T09:00:00"}
        result = compare_explanations(g, c)
        self.assertIn("same", result.lower())

    def test_compare_different_slots(self):
        g = {"start_time": "2026-04-01T09:00:00"}
        c = {"start_time": "2026-04-02T14:00:00"}
        result = compare_explanations(g, c)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 10)

    def test_schedule_summary_all_placed(self):
        tasks = [
            {"start_time": "2026-04-01T09:00:00", "duration": 60},
            {"start_time": "2026-04-01T10:00:00", "duration": 60},
        ]
        summary = generate_schedule_summary(tasks, 2)
        self.assertEqual(summary['placed'], 2)
        self.assertEqual(summary['unplaced'], 0)
        self.assertEqual(summary['success_rate'], 100)
        self.assertEqual(summary['total_hours'], 2.0)

    def test_schedule_summary_some_unplaced(self):
        tasks = [
            {"start_time": "2026-04-01T09:00:00", "duration": 60},
            {"duration": 60},
        ]
        summary = generate_schedule_summary(tasks, 2)
        self.assertEqual(summary['placed'], 1)
        self.assertEqual(summary['unplaced'], 1)
        self.assertEqual(summary['success_rate'], 50)

    def test_schedule_summary_empty(self):
        summary = generate_schedule_summary([], 0)
        self.assertEqual(summary['placed'], 0)
        self.assertEqual(summary['success_rate'], 0)


class TestMotivator(unittest.TestCase):

    def test_greeting_returns_string(self):
        result = get_greeting()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 5)

    def test_hype_message_returns_string(self):
        result = get_hype_message()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 5)

    def test_streak_milestone_messages(self):
        self.assertIn("3 DAY", get_streak_message(3))
        self.assertIn("5 DAY", get_streak_message(5))
        self.assertIn("1 FULL WEEK", get_streak_message(7))
        self.assertIn("21 DAYS", get_streak_message(21))

    def test_streak_non_milestone(self):
        result = get_streak_message(4)
        self.assertIn("4 days", result)
        self.assertIn("chain", result.lower())

    def test_recovery_message_returns_string(self):
        result = get_recovery_message()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 10)

    def test_focus_tip_returns_string(self):
        result = get_focus_tip()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 10)


class TestPriorityWeight(unittest.TestCase):

    def test_high_is_lowest_weight(self):
        self.assertEqual(get_priority_weight("High"), 1)

    def test_medium_weight(self):
        self.assertEqual(get_priority_weight("Medium"), 2)

    def test_low_is_highest_weight(self):
        self.assertEqual(get_priority_weight("Low"), 3)

    def test_unknown_defaults_to_low(self):
        self.assertEqual(get_priority_weight("Unknown"), 3)


class TestTimeWindows(unittest.TestCase):

    def test_morning_window(self):
        start, end = parse_time_window("Morning", 8, 22)
        self.assertEqual(start, 8)
        self.assertEqual(end, 12)

    def test_afternoon_window(self):
        start, end = parse_time_window("Afternoon", 8, 22)
        self.assertEqual(start, 12)
        self.assertEqual(end, 17)

    def test_evening_window(self):
        start, end = parse_time_window("Evening", 8, 22)
        self.assertEqual(start, 17)
        self.assertEqual(end, 22)

    def test_any_uses_full_range(self):
        start, end = parse_time_window("Any", 8, 22)
        self.assertEqual(start, 8)
        self.assertEqual(end, 22)


class TestOverlapDetection(unittest.TestCase):

    def test_detects_overlapping_tasks(self):
        tasks = [
            {"id": "1", "name": "Maths", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00"},
            {"id": "2", "name": "Physics", "start_time": "2026-04-01T10:30:00", "end_time": "2026-04-01T11:30:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 1)

    def test_no_overlap_when_tasks_adjacent(self):
        tasks = [
            {"id": "1", "name": "Maths", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00"},
            {"id": "2", "name": "Physics", "start_time": "2026-04-01T11:00:00", "end_time": "2026-04-01T12:00:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 0)

    def test_no_overlap_different_days(self):
        tasks = [
            {"id": "1", "name": "Maths", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00"},
            {"id": "2", "name": "Physics", "start_time": "2026-04-02T10:00:00", "end_time": "2026-04-02T11:00:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 0)

    def test_complete_overlap(self):
        tasks = [
            {"id": "1", "name": "Maths", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T12:00:00"},
            {"id": "2", "name": "Physics", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T12:00:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 1)

    def test_multiple_overlaps(self):
        tasks = [
            {"id": "1", "name": "A", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00"},
            {"id": "2", "name": "B", "start_time": "2026-04-01T10:30:00", "end_time": "2026-04-01T11:30:00"},
            {"id": "3", "name": "C", "start_time": "2026-04-01T10:45:00", "end_time": "2026-04-01T11:45:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertGreaterEqual(len(overlaps), 2)

    def test_handles_empty_list(self):
        overlaps = detect_all_overlaps([])
        self.assertEqual(len(overlaps), 0)

    def test_handles_missing_times(self):
        tasks = [
            {"id": "1", "name": "Maths", "start_time": None, "end_time": None},
            {"id": "2", "name": "Physics", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 0)


class TestSafeParseDatetime(unittest.TestCase):

    def test_standard_iso_format(self):
        result = safe_parse_datetime("2026-04-01T10:00:00")
        self.assertEqual(result, datetime(2026, 4, 1, 10, 0))

    def test_with_timezone(self):
        result = safe_parse_datetime("2026-04-01T10:00:00+00:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 10)

    def test_with_z_suffix(self):
        result = safe_parse_datetime("2026-04-01T10:00:00Z")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 10)

    def test_none_input(self):
        result = safe_parse_datetime(None)
        self.assertIsNone(result)

    def test_empty_string(self):
        result = safe_parse_datetime("")
        self.assertIsNone(result)

    def test_invalid_format(self):
        result = safe_parse_datetime("not a date")
        self.assertIsNone(result)


class TestFindNearestFreeSlot(unittest.TestCase):

    def test_finds_empty_slot(self):
        task = {"duration": 60}
        anchor = datetime(2026, 4, 1, 10, 0)
        start, end = find_nearest_free_slot(task, [], anchor, 8, 22, 15)
        self.assertIsNotNone(start)
        self.assertIsNotNone(end)
        self.assertEqual((end - start).total_seconds(), 3600)

    def test_avoids_booked_slot(self):
        task = {"duration": 60}
        booked = [(datetime(2026, 4, 1, 8, 0), datetime(2026, 4, 1, 9, 0))]
        anchor = datetime(2026, 4, 1, 8, 0)
        start, end = find_nearest_free_slot(task, booked, anchor, 8, 22, 15)
        self.assertIsNotNone(start)
        self.assertGreaterEqual(start, datetime(2026, 4, 1, 9, 15))

    def test_respects_break_time(self):
        task = {"duration": 60}
        booked = [(datetime(2026, 4, 1, 8, 0), datetime(2026, 4, 1, 9, 0))]
        anchor = datetime(2026, 4, 1, 8, 0)
        start, end = find_nearest_free_slot(task, booked, anchor, 8, 22, 30)
        self.assertIsNotNone(start)
        self.assertGreaterEqual(start, datetime(2026, 4, 1, 9, 30))


class TestICSExport(unittest.TestCase):

    def test_generates_ics_bytes(self):
        tasks = [
            {"name": "Test Task", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": ""},
        ]
        result = generate_ics_file(tasks)
        self.assertIsInstance(result, bytes)

    def test_ics_contains_event(self):
        tasks = [
            {"name": "Test Task", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": ""},
        ]
        result = generate_ics_file(tasks).decode('utf-8')
        self.assertIn("BEGIN:VCALENDAR", result)
        self.assertIn("BEGIN:VEVENT", result)
        self.assertIn("Test Task", result)
        self.assertIn("END:VCALENDAR", result)

    def test_multiple_events(self):
        tasks = [
            {"name": "Task 1", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": ""},
            {"name": "Task 2", "start_time": "2026-04-01T12:00:00", "end_time": "2026-04-01T13:00:00", "notes": ""},
        ]
        result = generate_ics_file(tasks).decode('utf-8')
        self.assertEqual(result.count("BEGIN:VEVENT"), 2)

    def test_empty_tasks(self):
        result = generate_ics_file([])
        self.assertIsInstance(result, bytes)
        decoded = result.decode('utf-8')
        self.assertIn("BEGIN:VCALENDAR", decoded)
        self.assertNotIn("BEGIN:VEVENT", decoded)


if __name__ == "__main__":
    unittest.main()