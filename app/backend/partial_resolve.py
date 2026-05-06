"""
partial_resolve.py — Overlap Detection and Conflict Resolution
Detects time conflicts between scheduled tasks and resolves them by
moving lower-priority tasks to the nearest free slot.
Implements FR-11.
"""
from datetime import datetime, timedelta
from app.backend.database import get_connection


def safe_parse_datetime(dt_string):
    if not dt_string:
        return None
    try:
        cleaned = dt_string.replace('Z', '+00:00')
        if '+' in cleaned[10:]:
            cleaned = cleaned[:cleaned.index('+', 10)]
        elif cleaned.count('-') > 2:
            last_dash = cleaned.rfind('-')
            if last_dash > 10:
                cleaned = cleaned[:last_dash]
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        try:
            return datetime.strptime(dt_string[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            return None


def detect_all_overlaps(tasks):
    overlaps = []
    seen = set()

    for i, t1 in enumerate(tasks):
        s1 = safe_parse_datetime(t1.get('start_time'))
        e1 = safe_parse_datetime(t1.get('end_time'))
        if not s1 or not e1:
            continue

        for j, t2 in enumerate(tasks):
            if j <= i:
                continue
            s2 = safe_parse_datetime(t2.get('start_time'))
            e2 = safe_parse_datetime(t2.get('end_time'))
            if not s2 or not e2:
                continue

            if s1 < e2 and s2 < e1:
                pair_key = tuple(sorted([t1['id'], t2['id']]))
                if pair_key not in seen:
                    seen.add(pair_key)
                    overlaps.append((t1, t2))

    return overlaps


def find_nearest_free_slot(task, booked_slots, anchor_time, day_start, day_end, break_mins):
    duration = task.get('duration', 60)
    anchor_date = anchor_time.date()

    search_start = datetime.combine(anchor_date, datetime.min.time()).replace(hour=day_start)
    search_end = datetime.combine(anchor_date, datetime.min.time()).replace(hour=day_end)

    current_time = search_start
    while current_time + timedelta(minutes=duration) <= search_end:
        proposed_end = current_time + timedelta(minutes=duration)

        overlap = False
        for b_start, b_end in booked_slots:
            if current_time < b_end and proposed_end > b_start:
                overlap = True
                current_time = b_end + timedelta(minutes=break_mins)
                break

        if not overlap:
            return current_time, proposed_end

    for day_offset in [1, -1, 2, -2, 3]:
        alt_date = anchor_date + timedelta(days=day_offset)
        alt_start = datetime.combine(alt_date, datetime.min.time()).replace(hour=day_start)
        alt_end = datetime.combine(alt_date, datetime.min.time()).replace(hour=day_end)

        current_time = alt_start
        while current_time + timedelta(minutes=duration) <= alt_end:
            proposed_end = current_time + timedelta(minutes=duration)

            overlap = False
            for b_start, b_end in booked_slots:
                if current_time < b_end and proposed_end > b_start:
                    overlap = True
                    current_time = b_end + timedelta(minutes=break_mins)
                    break

            if not overlap:
                return current_time, proposed_end

    return None, None


def resolve_overlaps(tasks, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
    raw_prefs = {row['key']: row['value'] for row in cursor.fetchall()}
    def safe_int(val, default):
        try: return int(val)
        except (ValueError, TypeError): return default
    day_start = safe_int(raw_prefs.get('day_start'), 8)
    day_end = safe_int(raw_prefs.get('day_end'), 22)
    break_mins = safe_int(raw_prefs.get('break_mins'), 15)

    overlaps = detect_all_overlaps(tasks)
    if not overlaps:
        conn.close()
        return []

    tasks_to_move = set()
    for t1, t2 in overlaps:
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        p1 = priority_order.get(t1.get('priority', 'Medium'), 2)
        p2 = priority_order.get(t2.get('priority', 'Medium'), 2)

        if t1.get('is_fixed') and not t2.get('is_fixed'):
            tasks_to_move.add(t2['id'])
        elif t2.get('is_fixed') and not t1.get('is_fixed'):
            tasks_to_move.add(t1['id'])
        elif p1 <= p2:
            tasks_to_move.add(t2['id'])
        else:
            tasks_to_move.add(t1['id'])

    booked_slots = []
    for t in tasks:
        if t['id'] in tasks_to_move:
            continue
        s = safe_parse_datetime(t.get('start_time'))
        e = safe_parse_datetime(t.get('end_time'))
        if s and e:
            booked_slots.append((s, e))

    resolved = []
    for t in tasks:
        if t['id'] not in tasks_to_move:
            continue

        anchor = safe_parse_datetime(t['start_time'])
        if not anchor:
            continue

        slot_start, slot_end = find_nearest_free_slot(
            t, booked_slots, anchor, day_start, day_end, break_mins
        )

        if slot_start and slot_end:
            cursor.execute("UPDATE tasks SET start_time = ?, end_time = ? WHERE id = ?",
                           (slot_start.isoformat(), slot_end.isoformat(), t['id']))
            booked_slots.append((slot_start, slot_end))
            resolved.append({
                "name": t['name'],
                "old_time": anchor.strftime('%H:%M'),
                "new_time": slot_start.strftime('%H:%M'),
                "new_day": slot_start.strftime('%A')
            })

    conn.commit()
    conn.close()
    return resolved