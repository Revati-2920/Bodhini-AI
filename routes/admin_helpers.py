"""Shared helpers for admin routes."""
from datetime import datetime
from sqlalchemy import func, or_, desc, asc
from database import (
    db, User, ResumeAnalysis, PlacementPrediction,
    InterviewHistory, SkillGapAnalysis, AIChatLog,
    CareerRoadmap, Announcement, AdminSettings,
)


def now_str():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def paginate(query, page, per_page=10):
    page = max(1, page)
    per_page = min(max(per_page, 5), 100)
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total, page, per_page, pages


def apply_sort(query, model, sort_by, order, allowed):
    if sort_by in allowed:
        col = getattr(model, sort_by)
        query = query.order_by(desc(col) if order == 'desc' else asc(col))
    return query


def get_settings():
    settings = AdminSettings.query.first()
    if not settings:
        settings = AdminSettings(updated_at=now_str())
        db.session.add(settings)
        db.session.commit()
    return settings


def get_analytics():
    total_users = User.query.filter_by(is_admin=False).count()
    total_resumes = ResumeAnalysis.query.count()
    total_chats = AIChatLog.query.count()
    total_placements = PlacementPrediction.query.count()
    total_interviews = InterviewHistory.query.count()
    total_skill_gaps = SkillGapAnalysis.query.count()
    total_roadmaps = CareerRoadmap.query.count()
    active_today = User.query.filter(
        User.is_admin == False,
        User.last_login.isnot(None),
    ).count()

    avg_ats = db.session.query(func.avg(ResumeAnalysis.ats_score)).scalar() or 0
    avg_resume = db.session.query(func.avg(ResumeAnalysis.resume_score)).scalar() or 0
    avg_placement = db.session.query(func.avg(PlacementPrediction.prediction_score)).scalar() or 0

    colleges = {}
    for u in User.query.filter_by(is_admin=False).all():
        if u.college:
            colleges[u.college] = colleges.get(u.college, 0) + 1
    top_colleges = sorted(colleges.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        'total_users': total_users,
        'total_resumes': total_resumes,
        'total_chats': total_chats,
        'total_placements': total_placements,
        'total_interviews': total_interviews,
        'total_skill_gaps': total_skill_gaps,
        'total_roadmaps': total_roadmaps,
        'active_today': active_today,
        'avg_ats': round(avg_ats, 1),
        'avg_resume': round(avg_resume, 1),
        'avg_placement': round(avg_placement, 1),
        'top_colleges': top_colleges,
    }


def chart_data():
    users = User.query.filter_by(is_admin=False).all()
    monthly_regs = {}
    for u in users:
        if u.created_at:
            key = u.created_at[:7]
            monthly_regs[key] = monthly_regs.get(key, 0) + 1

    resumes = ResumeAnalysis.query.all()
    resume_trends = {}
    for r in resumes:
        if r.created_at:
            key = r.created_at[:10]
            resume_trends[key] = resume_trends.get(key, 0) + 1

    ats_scores = [r.ats_score or 0 for r in resumes if r.ats_score]
    placement_scores = [p.prediction_score or 0 for p in PlacementPrediction.query.all()]

    chats = AIChatLog.query.all()
    chat_usage = {}
    for c in chats:
        if c.created_at:
            key = c.created_at[:10]
            chat_usage[key] = chat_usage.get(key, 0) + 1

    modules = {}
    for c in chats:
        mod = c.module_used or 'AI Career Chat'
        modules[mod] = modules.get(mod, 0) + 1

    interviews = InterviewHistory.query.all()
    interview_perf = [i.overall_score or 0 for i in interviews if i.overall_score]

    skill_gaps = SkillGapAnalysis.query.all()
    missing_skill_counts = {}
    career_interests = {}
    import json
    for sg in skill_gaps:
        if sg.career_goal:
            career_interests[sg.career_goal] = career_interests.get(sg.career_goal, 0) + 1
        try:
            skills = json.loads(sg.missing_skills) if sg.missing_skills else []
            if isinstance(skills, list):
                for s in skills:
                    name = s if isinstance(s, str) else s.get('skill', str(s))
                    missing_skill_counts[name] = missing_skill_counts.get(name, 0) + 1
        except Exception:
            pass

    top_missing = sorted(missing_skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_careers = sorted(career_interests.items(), key=lambda x: x[1], reverse=True)[:8]

    daily_active = {}
    for u in users:
        if u.last_login:
            key = u.last_login[:10]
            daily_active[key] = daily_active.get(key, 0) + 1

    ats_distribution = {'0-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for s in ats_scores:
        if s <= 40:
            ats_distribution['0-40'] += 1
        elif s <= 60:
            ats_distribution['41-60'] += 1
        elif s <= 80:
            ats_distribution['61-80'] += 1
        else:
            ats_distribution['81-100'] += 1

    colleges = {}
    for u in users:
        if u.college:
            colleges[u.college] = colleges.get(u.college, 0) + 1

    return {
        'monthly_regs': monthly_regs,
        'daily_active': daily_active,
        'resume_trends': resume_trends,
        'avg_ats': round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else 0,
        'placement_scores': placement_scores,
        'chat_usage': chat_usage,
        'modules': modules,
        'interview_perf': interview_perf,
        'top_missing': top_missing,
        'top_careers': top_careers,
        'ats_distribution': ats_distribution,
        'top_colleges': sorted(colleges.items(), key=lambda x: x[1], reverse=True)[:8],
        'ai_requests': len(chats),
    }


def user_search_query(q, status=None, department=None):
    query = User.query.filter_by(is_admin=False)
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            User.username.ilike(like),
            User.email.ilike(like),
            User.college.ilike(like),
            User.department.ilike(like),
        ))
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'disabled':
        query = query.filter_by(is_active=False)
    if department:
        query = query.filter(User.department.ilike(f'%{department}%'))
    return query
