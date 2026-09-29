from datetime import date, datetime, timedelta, timezone


def build_tasks(exams, completed_by_exam):
    """Generate date-aware module tasks across all active exams."""
    today = date.today()
    tasks = []
    for exam, subject in exams:
        remaining = max(0, exam.total_modules - completed_by_exam.get(exam.id, 0))
        days = max(1, (exam.exam_date - today).days)
        for module in range(remaining):
            offset = min(days - 1, int(module * days / max(1, remaining)))
            scheduled = today + timedelta(days=max(0, offset))
            ratio = (offset + 1) / days
            phase = "Study" if ratio <= .6 else "Revision" if ratio <= .85 else "Final review"
            tasks.append({"exam_id": exam.id, "subject_id": subject.id,
                          "title": f"{subject.name} · Module {completed_by_exam.get(exam.id, 0) + module + 1}",
                          "scheduled_for": scheduled, "phase": phase, "position": module + 1})
    return sorted(tasks, key=lambda task: (task["scheduled_for"], task["exam_id"], task["position"]))


def feasibility(exams, task_rows):
    today = date.today()
    completed = {exam.id: 0 for exam, _ in exams}
    for task in task_rows:
        if task.completed: completed[task.exam_id] = completed.get(task.exam_id, 0) + 1
    cards = []
    for exam, subject in exams:
        days = max(0, (exam.exam_date - today).days)
        done = completed.get(exam.id, 0)
        remaining = max(0, exam.total_modules - done)
        needed = remaining / max(1, days)
        # One module normally takes a 50-minute focused block.
        capacity = exam.daily_minutes / 50
        status = "on-track" if needed <= capacity else "at-risk" if needed <= capacity * 1.35 else "unrealistic"
        cards.append({"exam_id": exam.id, "name": exam.name, "subject": subject.name,
                      "exam_date": exam.exam_date.isoformat(), "days_left": days, "total_modules": exam.total_modules,
                      "completed_modules": done, "remaining_modules": remaining, "daily_target": round(needed, 1),
                      "capacity": round(capacity, 1), "status": status})
    return sorted(cards, key=lambda c: (c["days_left"], -c["remaining_modules"]))


def priority(cards, subject_stats):
    performance = {item["subject"]: item["average_productivity"] for item in subject_stats}
    ranked = []
    for card in cards:
        urgency = 1 / max(1, card["days_left"])
        workload = card["remaining_modules"] / max(1, card["total_modules"])
        growth = (5 - performance.get(card["subject"], 3)) / 5
        score = urgency * 55 + workload * 30 + growth * 15
        ranked.append({**card, "priority_score": round(score * 100),
                       "reason": f"{card['days_left']} days left, {card['remaining_modules']} modules remaining"})
    return sorted(ranked, key=lambda item: item["priority_score"], reverse=True)
