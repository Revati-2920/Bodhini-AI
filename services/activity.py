"""Activity timeline aggregation."""
from database import (
    ResumeAnalysis, PlacementPrediction, CareerRoadmap,
    InterviewHistory, SkillGapAnalysis, AIChatLog, ActivityLog,
)


def log_activity(user_id, action_type, description, meta=None):
    from datetime import datetime
    import json
    from database import db

    entry = ActivityLog(
        user_id=user_id,
        action_type=action_type,
        description=description,
        meta_json=json.dumps(meta or {}),
        created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
    )
    db.session.add(entry)
    return entry


def get_activity_timeline(user_id, limit=15):
    """Merge ActivityLog + legacy data from module tables."""
    activities = []

    logs = ActivityLog.query.filter_by(user_id=user_id).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    for log in logs:
        activities.append({
            'date': log.created_at,
            'activity': log.description,
            'type': log.action_type,
            'status': 'Completed',
        })

    if len(activities) < limit:
        for r in ResumeAnalysis.query.filter_by(user_id=user_id).order_by(ResumeAnalysis.created_at.desc()).limit(5).all():
            activities.append({'date': r.created_at, 'activity': f'Resume Uploaded: {r.resume_name}', 'type': 'resume', 'status': 'Completed'})
        for p in PlacementPrediction.query.filter_by(user_id=user_id).order_by(PlacementPrediction.created_at.desc()).limit(5).all():
            activities.append({'date': p.created_at, 'activity': 'Placement Prediction Generated', 'type': 'placement', 'status': 'Completed'})
        for i in InterviewHistory.query.filter_by(user_id=user_id).order_by(InterviewHistory.created_at.desc()).limit(5).all():
            activities.append({'date': i.created_at, 'activity': f'Interview Completed ({i.interview_type})', 'type': 'interview', 'status': 'Completed'})
        for r in CareerRoadmap.query.filter_by(user_id=user_id).order_by(CareerRoadmap.created_at.desc()).limit(5).all():
            activities.append({'date': r.created_at, 'activity': f'Roadmap Created: {r.career_goal}', 'type': 'roadmap', 'status': 'Completed'})
        for s in SkillGapAnalysis.query.filter_by(user_id=user_id).order_by(SkillGapAnalysis.created_at.desc()).limit(5).all():
            activities.append({'date': s.created_at, 'activity': 'Skill Gap Analysis Completed', 'type': 'skill_gap', 'status': 'Completed'})
        for c in AIChatLog.query.filter_by(user_id=user_id).order_by(AIChatLog.created_at.desc()).limit(5).all():
            activities.append({'date': c.created_at, 'activity': 'AI Chat Session', 'type': 'chat', 'status': 'Completed'})

    activities.sort(key=lambda x: x.get('date') or '', reverse=True)
    seen = set()
    unique = []
    for a in activities:
        key = (a['date'], a['activity'])
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique[:limit]
