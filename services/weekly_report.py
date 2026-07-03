"""Weekly AI report generator."""
from datetime import datetime, timedelta
from services.career_score import compute_career_scores
from services.recommendations import get_recommendations
from services.activity import get_activity_timeline
from database import (
    User, ResumeAnalysis, PlacementPrediction,
    InterviewHistory, SkillGapAnalysis, UserCertificate,
)


def generate_weekly_report(user_id):
    user = User.query.get(user_id)
    scores = compute_career_scores(user_id, (
        User, ResumeAnalysis, PlacementPrediction,
        InterviewHistory, SkillGapAnalysis, UserCertificate,
    ))
    recommendations = get_recommendations(user_id)
    activities = get_activity_timeline(user_id, limit=10)

    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
    resumes = ResumeAnalysis.query.filter(
        ResumeAnalysis.user_id == user_id,
        ResumeAnalysis.created_at >= week_ago,
    ).count()
    interviews = InterviewHistory.query.filter(
        InterviewHistory.user_id == user_id,
        InterviewHistory.created_at >= week_ago,
    ).count()
    certs = UserCertificate.query.filter(
        UserCertificate.user_id == user_id,
        UserCertificate.created_at >= week_ago,
    ).count()

    return {
        'user': user,
        'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'scores': scores,
        'resume_improvements': resumes,
        'ats_progress': scores['ats_score'],
        'placement_readiness': scores['placement_score'],
        'interview_practice': interviews,
        'skills_learned': scores['skill_score'],
        'courses_completed': certs,
        'recommendations': recommendations,
        'activities': activities,
        'grade': scores['grade'],
    }
