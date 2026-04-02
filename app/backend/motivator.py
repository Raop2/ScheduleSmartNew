import random
from datetime import datetime
from app.backend.database import get_connection


def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return random.choice(["Good morning! Ready to own today?", "Morning! Let's build some momentum."])
    elif hour < 18:
        return random.choice(["Good afternoon! Stay locked in.", "Afternoon check-in. Keep pushing."])
    return random.choice(["Evening session. Let's finish strong.", "Late grind. You've got this."])


def get_hype_message():
    messages = [
        "LET'S GO! You smashed that session!",
        "Built different. You just proved it.",
        "Another one down. The results are compounding.",
        "Zero hesitation. Great execution.",
        "That is how it's done."
    ]
    return random.choice(messages)


def get_streak_message(streak_count):
    milestones = {
        3: "3 DAY STREAK! The habit is forming.",
        5: "5 DAY STREAK! You're absolutely locked in!",
        7: "1 FULL WEEK! Flawless consistency.",
        10: "DOUBLE DIGITS! 10 days of pure focus.",
        14: "2 WEEKS! You are unstoppable right now.",
        21: "21 DAYS! The habit is permanent.",
        30: "1 MONTH! Elite discipline achieved."
    }
    return milestones.get(streak_count, f"{streak_count} days strong. Keep the chain unbroken.")


def get_recovery_message():
    messages = [
        "You can still turn this around. Start with one small step.",
        "A minor setback. Reset and execute.",
        "Don't look at the whole mountain. Just take the next step.",
        "Momentum is built one task at a time. Grab an easy win."
    ]
    return random.choice(messages)


def get_focus_tip():
    tips = [
        "Hydration check. Drink some water before the next block.",
        "Fix your posture. Deep breath. Engage.",
        "If you hit a wall, summarize what you know so far out loud.",
        "Close unnecessary tabs. Guard your attention.",
        "Visualize the feeling of having this completely finished."
    ]
    return random.choice(tips)


def get_smart_suggestion(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND module != 'Break' AND end_time IS NOT NULL AND user_id = ?", (user_id,))
    all_pending = [dict(row) for row in cursor.fetchall()]
    overdue = []
    for t in all_pending:
        try:
            end_dt = datetime.fromisoformat(t['end_time'])
            if end_dt < now:
                overdue.append(t)
        except (ValueError, TypeError):
            pass

    if overdue:
        names = [t['name'] for t in overdue[:3]]
        conn.close()
        if len(overdue) == 1:
            return f"You have 1 overdue task: {names[0]}. Complete it now to get back on track."
        else:
            return f"You have {len(overdue)} overdue tasks including {', '.join(names)}. Start with the quickest one to build momentum."

    cursor.execute("SELECT module, SUM(duration) as total_dur FROM completion_log WHERE user_id = ? GROUP BY module ORDER BY total_dur DESC LIMIT 1", (user_id,))
    top_module_row = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM completion_log WHERE completion_date = ? AND user_id = ?", (now.date().isoformat(), user_id))
    today_count = cursor.fetchone()['count']

    conn.close()

    if today_count > 4:
        return "You've been grinding hard today. Don't forget to schedule a proper break to avoid burnout."

    if top_module_row and top_module_row['total_dur']:
        top_module = top_module_row['module']
        hours = round(top_module_row['total_dur'] / 60, 1)
        return f"My analysis shows deep focus on {top_module} ({hours}h logged). Ensure you are balancing your other modules."

    return "Your schedule is a blank canvas. Start by knocking out your highest priority task first to build immediate momentum."