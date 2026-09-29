from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean


def _round(value):
    return round(value, 1) if value is not None else None


def analyze(rows):
    """Return explainable analytics from session/subject joined rows."""
    sessions = list(rows)
    if not sessions:
        return {"sample_count": 0, "average_productivity": None, "average_minutes": None,
                "weekly_minutes": 0, "subject_stats": [], "insights": [], "timeline": []}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    weekly = sum(session.duration_minutes for session, _ in sessions if session.started_at.replace(tzinfo=None) >= now - timedelta(days=7))
    by_subject = defaultdict(list)
    by_mood = defaultdict(list)
    short, long = [], []
    timeline = []
    for session, subject in sessions:
        by_subject[subject.name].append(session)
        by_mood[session.mood].append(session.productivity)
        (short if session.duration_minutes <= 120 else long).append(session.productivity)
        timeline.append({"date": session.started_at.date().isoformat(), "productivity": session.productivity,
                         "minutes": session.duration_minutes, "subject": subject.name})
    subject_stats = sorted([
        {"subject": name, "sessions": len(items), "average_productivity": _round(mean(x.productivity for x in items)),
         "minutes": sum(x.duration_minutes for x in items)} for name, items in by_subject.items()
    ], key=lambda x: x["average_productivity"], reverse=True)
    insights = []
    if len(sessions) < 3:
        insights.append({"tone": "neutral", "title": "Build your baseline", "body": f"Log {3-len(sessions)} more session{'s' if len(sessions) != 2 else ''} to unlock pattern comparisons."})
    if by_mood.get(4) or by_mood.get(5):
        high = [*by_mood[4], *by_mood[5]]
        low = [*by_mood[1], *by_mood[2], *by_mood[3]]
        if high and low and abs(mean(high)-mean(low)) >= .4:
            better = "higher" if mean(high) > mean(low) else "lower"
            insights.append({"tone": "positive", "title": "Mood matters", "body": f"Your {better}-mood sessions average {abs(mean(high)-mean(low)):.1f} points different in productivity."})
    if short and long and mean(short) - mean(long) >= .5:
        insights.append({"tone": "warning", "title": "Long-session dip", "body": "Sessions of two hours or less are currently more productive; schedule a deliberate break before extending one."})
    if len(subject_stats) >= 2 and subject_stats[0]["average_productivity"] - subject_stats[-1]["average_productivity"] >= .7:
        insights.append({"tone": "neutral", "title": f"Focus opportunity: {subject_stats[-1]['subject']}", "body": f"It trails your strongest subject by {subject_stats[0]['average_productivity'] - subject_stats[-1]['average_productivity']:.1f} points. Use a high-energy window for it."})
    return {"sample_count": len(sessions), "average_productivity": _round(mean(session.productivity for session, _ in sessions)),
            "average_minutes": _round(mean(session.duration_minutes for session, _ in sessions)), "weekly_minutes": weekly,
            "subject_stats": subject_stats, "insights": insights[:3], "timeline": sorted(timeline, key=lambda x: x["date"])}
