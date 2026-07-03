"""Personalized AI recommendations engine."""
import json
from database import (
    ResumeAnalysis, PlacementPrediction, InterviewHistory,
    SkillGapAnalysis, Company, User,
)


def get_recommendations(user_id):
    user = User.query.get(user_id)
    recs = []

    resumes = ResumeAnalysis.query.filter_by(user_id=user_id).order_by(ResumeAnalysis.created_at.desc()).all()
    placements = PlacementPrediction.query.filter_by(user_id=user_id).order_by(PlacementPrediction.created_at.desc()).all()
    interviews = InterviewHistory.query.filter_by(user_id=user_id).all()
    skill_gaps = SkillGapAnalysis.query.filter_by(user_id=user_id).order_by(SkillGapAnalysis.created_at.desc()).all()

    if not resumes:
        recs.append({'icon': '📄', 'title': 'Upload Your Resume', 'desc': 'Get your ATS score and improve your chances.', 'link': '/ats-resume-checker', 'priority': 'high'})
    elif resumes[0].ats_score and resumes[0].ats_score < 70:
        recs.append({'icon': '📝', 'title': 'Update Resume', 'desc': f'Your ATS score is {resumes[0].ats_score}%. Improve keywords and formatting.', 'link': '/ats-resume-checker', 'priority': 'high'})

    if skill_gaps:
        try:
            missing = json.loads(skill_gaps[0].missing_skills or '[]')
            if missing:
                skill = missing[0] if isinstance(missing[0], str) else missing[0].get('skill', 'SQL')
                recs.append({'icon': '📚', 'title': f'Improve {skill}', 'desc': 'Close your top skill gap for better placement readiness.', 'link': '/skill-gap', 'priority': 'high'})
        except Exception:
            recs.append({'icon': '📚', 'title': 'Improve SQL', 'desc': 'Practice database skills for placement interviews.', 'link': '/skill-gap', 'priority': 'medium'})

    recs.append({'icon': '💻', 'title': 'Practice DSA', 'desc': 'Solve 2 coding problems today for interview readiness.', 'link': '/interview', 'priority': 'medium'})

    if not interviews or len(interviews) < 3:
        recs.append({'icon': '🎤', 'title': 'Complete Interview Round', 'desc': 'Practice a mock interview to boost confidence.', 'link': '/interview', 'priority': 'high'})

    if not placements:
        recs.append({'icon': '🎯', 'title': 'Check Placement Readiness', 'desc': 'Run the placement predictor to know your chances.', 'link': '/placement-predictor', 'priority': 'medium'})

    company = Company.query.filter_by(is_active=True).order_by(Company.created_at.desc()).first()
    if company:
        recs.append({'icon': '🏢', 'title': f'Apply for {company.name}', 'desc': f'Package: {company.package or "TBD"}. Deadline: {company.application_deadline or "Soon"}.', 'link': f'/companies/{company.id}', 'priority': 'medium'})

    if user and user.dream_company:
        dream = Company.query.filter(Company.name.ilike(f'%{user.dream_company}%')).first()
        if dream:
            recs.append({'icon': '⭐', 'title': f'Prepare for {user.dream_company}', 'desc': 'Review interview questions and preparation tips.', 'link': f'/companies/{dream.id}', 'priority': 'high'})

    return recs[:6]
