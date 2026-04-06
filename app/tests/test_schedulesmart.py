import sys
import os
import unittest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, date, timedelta

root_path = Path(__file__).resolve().parent.parent
sys.path.append(str(root_path))

from app.backend.greedy_scheduler import generate_greedy_schedule, get_priority_weight, parse_time_window
from app.backend.explanation import build_greedy_reason, build_cpsat_reason, compare_explanations, generate_schedule_summary
from app.backend.motivator import get_greeting, get_hype_message, get_streak_message, get_recovery_message, get_focus_tip
from app.backend.export_service import generate_ics_file
from app.backend.partial_resolve import safe_parse_datetime, detect_all_overlaps, find_nearest_free_slot
from app.backend.curriculum import generate_curriculum, match_subject, CURRICULUM_DB, KEYWORD_ALIASES
from app.backend.database import hash_password

try:
    from app.backend.cpsat_scheduler import generate_cpsat_schedule
    CPSAT_AVAILABLE = True
except (ImportError, OSError):
    CPSAT_AVAILABLE = False


# ===== GREEDY SCHEDULER =====

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
                self.assertIn('explanation', task)
                self.assertTrue(len(task['explanation']) > 10)

    def test_single_task_scheduling(self):
        tasks = [{"id": "1", "name": "Solo Task", "duration": 30, "priority": "Low", "deadline": None,
                  "preferred_time": "Any", "is_fixed": False, "start_time": None, "end_time": None, "notes": ""}]
        result = generate_greedy_schedule(tasks, self.start_date, 1, 8, 22, 6, 15)
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].get('start_time'))


# ===== CP-SAT SCHEDULER =====

@unittest.skipUnless(CPSAT_AVAILABLE, "CP-SAT not available on this machine")
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
            self.assertFalse(s < lecture_e and lecture_s < e, "Study overlaps with lecture")

    def test_empty_task_list(self):
        result = generate_cpsat_schedule([], self.start_date, 7, 8, 22, 6, 15)
        self.assertEqual(result, [])


# ===== EXPLANATION ENGINE =====

class TestExplanationEngine(unittest.TestCase):

    def test_greedy_reason_contains_text(self):
        task = {"priority": "High", "deadline": "2026-04-10", "preferred_time": "Morning"}
        reason = build_greedy_reason(task, datetime(2026, 4, 1, 9, 0), True)
        self.assertIsInstance(reason, str)
        self.assertTrue(len(reason) > 10)
        self.assertTrue(reason.endswith("."))

    def test_greedy_reason_outside_preferred_window(self):
        task = {"priority": "Medium", "preferred_time": "Morning"}
        reason = build_greedy_reason(task, datetime(2026, 4, 1, 14, 0), False)
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
        self.assertTrue(len(result) > 10)

    def test_compare_greedy_unplaced(self):
        g = {"start_time": "Unplaced"}
        c = {"start_time": "2026-04-01T09:00:00"}
        result = compare_explanations(g, c)
        self.assertIsInstance(result, str)

    def test_compare_cpsat_unplaced(self):
        g = {"start_time": "2026-04-01T09:00:00"}
        c = {"start_time": "Unplaced"}
        result = compare_explanations(g, c)
        self.assertIsInstance(result, str)

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
        tasks = [{"start_time": "2026-04-01T09:00:00", "duration": 60}, {"duration": 60}]
        summary = generate_schedule_summary(tasks, 2)
        self.assertEqual(summary['placed'], 1)
        self.assertEqual(summary['unplaced'], 1)
        self.assertEqual(summary['success_rate'], 50)

    def test_schedule_summary_empty(self):
        summary = generate_schedule_summary([], 0)
        self.assertEqual(summary['placed'], 0)
        self.assertEqual(summary['success_rate'], 0)


# ===== MOTIVATOR =====

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

    def test_greeting_varies(self):
        results = set(get_greeting() for _ in range(20))
        self.assertGreater(len(results), 1, "Greetings should have variety")

    def test_hype_message_varies(self):
        results = set(get_hype_message() for _ in range(20))
        self.assertGreater(len(results), 1, "Hype messages should have variety")


# ===== PRIORITY WEIGHT =====

class TestPriorityWeight(unittest.TestCase):

    def test_high_is_lowest_weight(self):
        self.assertEqual(get_priority_weight("High"), 1)

    def test_medium_weight(self):
        self.assertEqual(get_priority_weight("Medium"), 2)

    def test_low_is_highest_weight(self):
        self.assertEqual(get_priority_weight("Low"), 3)

    def test_unknown_defaults_to_low(self):
        self.assertEqual(get_priority_weight("Unknown"), 3)


# ===== TIME WINDOWS =====

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

    def test_morning_respects_late_start(self):
        start, end = parse_time_window("Morning", 10, 22)
        self.assertEqual(start, 10)
        self.assertEqual(end, 12)


# ===== OVERLAP DETECTION =====

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

    def test_one_minute_overlap(self):
        tasks = [
            {"id": "1", "name": "A", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:01:00"},
            {"id": "2", "name": "B", "start_time": "2026-04-01T11:00:00", "end_time": "2026-04-01T12:00:00"},
        ]
        overlaps = detect_all_overlaps(tasks)
        self.assertEqual(len(overlaps), 1)


# ===== SAFE PARSE DATETIME =====

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
        self.assertIsNone(safe_parse_datetime(None))

    def test_empty_string(self):
        self.assertIsNone(safe_parse_datetime(""))

    def test_invalid_format(self):
        self.assertIsNone(safe_parse_datetime("not a date"))

    def test_with_positive_offset(self):
        result = safe_parse_datetime("2026-04-01T10:00:00+05:30")
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 10)

    def test_with_negative_offset(self):
        result = safe_parse_datetime("2026-04-01T10:00:00-08:00")
        self.assertIsNotNone(result)


# ===== FIND NEAREST FREE SLOT =====

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
        start, end = find_nearest_free_slot(task, booked, datetime(2026, 4, 1, 8, 0), 8, 22, 30)
        self.assertIsNotNone(start)
        self.assertGreaterEqual(start, datetime(2026, 4, 1, 9, 30))

    def test_finds_slot_on_next_day(self):
        task = {"duration": 60}
        booked = [(datetime(2026, 4, 1, h, 0), datetime(2026, 4, 1, h + 1, 15)) for h in range(8, 22)]
        anchor = datetime(2026, 4, 1, 8, 0)
        start, end = find_nearest_free_slot(task, booked, anchor, 8, 22, 0)
        self.assertIsNotNone(start)
        self.assertNotEqual(start.date(), date(2026, 4, 1))


# ===== ICS EXPORT =====

class TestICSExport(unittest.TestCase):

    def test_generates_ics_bytes(self):
        tasks = [{"name": "Test", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": ""}]
        result = generate_ics_file(tasks)
        self.assertIsInstance(result, bytes)

    def test_ics_contains_event(self):
        tasks = [{"name": "Test Task", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": ""}]
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
        decoded = result.decode('utf-8')
        self.assertIn("BEGIN:VCALENDAR", decoded)
        self.assertNotIn("BEGIN:VEVENT", decoded)

    def test_notes_included(self):
        tasks = [{"name": "Study", "start_time": "2026-04-01T10:00:00", "end_time": "2026-04-01T11:00:00", "notes": "Chapter 5 focus"}]
        result = generate_ics_file(tasks).decode('utf-8')
        self.assertIn("Chapter 5 focus", result)


# ===== CURRICULUM ENGINE =====

class TestCurriculumMatchSubject(unittest.TestCase):

    def test_exact_match_python(self):
        result = match_subject("python")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Python Programming")

    def test_exact_match_calculus(self):
        result = match_subject("calculus")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Calculus")

    def test_alias_py(self):
        result = match_subject("py")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Python Programming")

    def test_alias_dsa(self):
        result = match_subject("dsa")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Data Structures and Algorithms")

    def test_alias_js(self):
        result = match_subject("js")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "JavaScript")

    def test_partial_match(self):
        result = match_subject("python programming basics")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Python Programming")

    def test_case_insensitive(self):
        result = match_subject("PYTHON")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Python Programming")

    def test_unrecognised_subject(self):
        result = match_subject("underwater basket weaving")
        self.assertIsNone(result)

    def test_alias_calc(self):
        result = match_subject("calc")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Calculus")

    def test_alias_exam(self):
        result = match_subject("exam")
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], "Exam Preparation")


class TestCurriculumGeneration(unittest.TestCase):

    def test_generates_correct_number_of_sessions(self):
        plan, name = generate_curriculum("python", 10)
        self.assertEqual(len(plan), 10)

    def test_recognised_subject_uses_topics(self):
        plan, name = generate_curriculum("python", 5)
        self.assertEqual(name, "Python Programming")
        self.assertIn("Python Programming:", plan[0])

    def test_unrecognised_subject_uses_generic(self):
        plan, name = generate_curriculum("random subject xyz", 5)
        self.assertEqual(len(plan), 5)
        self.assertIn("Random Subject Xyz", name)

    def test_sessions_exceed_topics_cycles(self):
        plan, name = generate_curriculum("python", 100)
        self.assertEqual(len(plan), 100)
        has_review = any("Review:" in p for p in plan)
        self.assertTrue(has_review, "Long plans should cycle with Review prefix")

    def test_each_session_is_unique_within_topics(self):
        plan, name = generate_curriculum("python", 10)
        self.assertEqual(len(set(plan)), 10, "First 10 sessions should all be different topics")

    def test_generic_plan_has_variety(self):
        plan, name = generate_curriculum("obscure topic", 10)
        unique_plans = set(plan)
        self.assertGreater(len(unique_plans), 5)

    def test_all_subjects_have_topics(self):
        for key, subject in CURRICULUM_DB.items():
            self.assertIn('name', subject, f"Subject {key} missing name")
            self.assertIn('topics', subject, f"Subject {key} missing topics")
            self.assertGreater(len(subject['topics']), 5, f"Subject {key} has too few topics")

    def test_all_aliases_map_to_valid_subjects(self):
        for alias, key in KEYWORD_ALIASES.items():
            self.assertIn(key, CURRICULUM_DB, f"Alias '{alias}' maps to missing subject '{key}'")


# ===== PASSWORD HASHING =====

class TestPasswordHashing(unittest.TestCase):

    def test_hash_returns_string(self):
        result = hash_password("test123")
        self.assertIsInstance(result, str)

    def test_hash_is_consistent(self):
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        self.assertEqual(h1, h2)

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        self.assertNotEqual(h1, h2)

    def test_hash_is_not_plaintext(self):
        result = hash_password("secret")
        self.assertNotEqual(result, "secret")
        self.assertNotIn("secret", result)

    def test_hash_has_fixed_length(self):
        h1 = hash_password("short")
        h2 = hash_password("a very long password with lots of characters")
        self.assertEqual(len(h1), len(h2))


# ===== CURRICULUM DATABASE COVERAGE =====

class TestCurriculumDatabaseCoverage(unittest.TestCase):

    def test_has_computer_science_subjects(self):
        cs_subjects = ["python", "java", "javascript", "c++", "sql", "data structures"]
        for s in cs_subjects:
            self.assertIn(s, CURRICULUM_DB, f"Missing CS subject: {s}")

    def test_has_maths_subjects(self):
        maths_subjects = ["calculus", "algebra", "statistics", "linear algebra"]
        for s in maths_subjects:
            self.assertIn(s, CURRICULUM_DB, f"Missing maths subject: {s}")

    def test_has_science_subjects(self):
        science_subjects = ["physics", "chemistry", "biology"]
        for s in science_subjects:
            self.assertIn(s, CURRICULUM_DB, f"Missing science subject: {s}")

    def test_has_humanities_subjects(self):
        humanities = ["psychology", "history", "english literature", "philosophy"]
        for s in humanities:
            self.assertIn(s, CURRICULUM_DB, f"Missing humanities subject: {s}")

    def test_has_academic_skills(self):
        skills = ["essay writing", "dissertation", "research methods", "exam prep"]
        for s in skills:
            self.assertIn(s, CURRICULUM_DB, f"Missing academic skill: {s}")

    def test_minimum_subject_count(self):
        self.assertGreaterEqual(len(CURRICULUM_DB), 30, "Should have at least 30 subjects")

    def test_minimum_alias_count(self):
        self.assertGreaterEqual(len(KEYWORD_ALIASES), 50, "Should have at least 50 aliases")


if __name__ == "__main__":
    unittest.main()