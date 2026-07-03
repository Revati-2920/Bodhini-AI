"""Career score computation for Bodhini AI."""
import json


def _grade(score):
    if score >= 90:
        return 'A+'
    if score >= 80:
        return 'A'
    if score >= 70:
        return 'B+'
    if score >= 60:
        return 'B'
    if score >= 50:
        return 'C'
    return 'D'


def compute_career_scores(user_id, db_models):
    """Return dict of all career scores for a user."""
    User, ResumeAnalysis, PlacementPrediction, InterviewHistory, SkillGapAnalysis, UserCertificate = db_models

    resumes = ResumeAnalysis.query.filter_by(user_id=user_id).order_by(ResumeAnalysis.created_at.desc()).all()
    placements = PlacementPrediction.query.filter_by(user_id=user_id).order_by(PlacementPrediction.created_at.desc()).all()
    interviews = InterviewHistory.query.filter_by(user_id=user_id).all()
    skill_gaps = SkillGapAnalysis.query.filter_by(user_id=user_id).order_by(SkillGapAnalysis.created_at.desc()).all()
    certs = UserCertificate.query.filter_by(user_id=user_id).count()

    resume_score = resumes[0].resume_score if resumes and resumes[0].resume_score else 0
    ats_score = resumes[0].ats_score if resumes and resumes[0].ats_score else 0
    placement_score = placements[0].prediction_score if placements and placements[0].prediction_score else 0

    if interviews:
        interview_score = round(sum(i.overall_score or 0 for i in interviews) / len(interviews) * 10)
    else:
        interview_score = 0

    skill_score = skill_gaps[0].skill_match if skill_gaps and skill_gaps[0].skill_match else 0
    cert_bonus = min(certs * 2, 10)

    weights = []
    values = []
    if resume_score:
        weights.append(0.15)
        values.append(resume_score)
    if ats_score:
        weights.append(0.2)
        values.append(ats_score)
    if placement_score:
        weights.append(0.25)
        values.append(placement_score)
    if interview_score:
        weights.append(0.2)
        values.append(interview_score)
    if skill_score:
        weights.append(0.2)
        values.append(skill_score)

    if weights:
        total_w = sum(weights)
        overall = round(sum(v * w for v, w in zip(values, weights)) / total_w + cert_bonus)
    else:
        overall = cert_bonus

    overall = min(100, max(0, overall))

    return {
        'overall': overall,
        'resume_score': resume_score,
        'ats_score': ats_score,
        'placement_score': placement_score,
        'interview_score': interview_score,
        'skill_score': skill_score,
        'grade': _grade(overall),
        'certificate_count': certs,
    }


def progress_chart_data(user_id, db_models):
    """Time-series data for student progress charts."""
    ResumeAnalysis, PlacementPrediction, InterviewHistory, SkillGapAnalysis = db_models

    resume_trend = [{'date': r.created_at[:10] if r.created_at else '', 'score': r.ats_score or 0}
                    for r in ResumeAnalysis.query.filter_by(user_id=user_id).order_by(ResumeAnalysis.created_at).all()]
    placement_trend = [{'date': p.created_at[:10] if p.created_at else '', 'score': p.prediction_score or 0}
                       for p in PlacementPrediction.query.filter_by(user_id=user_id).order_by(PlacementPrediction.created_at).all()]
    interview_trend = [{'date': i.created_at[:10] if i.created_at else '', 'score': round((i.overall_score or 0) * 10)}
                       for i in InterviewHistory.query.filter_by(user_id=user_id).order_by(InterviewHistory.created_at).all()]
    skill_trend = [{'date': s.created_at[:10] if s.created_at else '', 'score': s.skill_match or 0}
                   for s in SkillGapAnalysis.query.filter_by(user_id=user_id).order_by(SkillGapAnalysis.created_at).all()]

    career_trend = []
    for item in sorted(resume_trend + placement_trend + interview_trend + skill_trend, key=lambda x: x['date']):
        if item['date']:
            career_trend.append(item)

    return {
        'resume_trend': resume_trend[-12:],
        'ats_trend': resume_trend[-12:],
        'placement_trend': placement_trend[-12:],
        'interview_trend': interview_trend[-12:],
        'skill_trend': skill_trend[-12:],
        'career_trend': career_trend[-12:],
    }
