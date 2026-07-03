"""Gamification: XP, levels, badges, streaks."""
import json
from datetime import datetime, timedelta

from database import db, UserGamification

BADGE_DEFS = {
    'career_explorer': {'name': 'Career Explorer', 'xp': 50, 'icon': '🧭'},
    'resume_master': {'name': 'Resume Master', 'xp': 100, 'icon': '📄'},
    'interview_expert': {'name': 'Interview Expert', 'xp': 150, 'icon': '🎤'},
    'placement_ready': {'name': 'Placement Ready', 'xp': 200, 'icon': '🎯'},
    'skill_builder': {'name': 'Skill Builder', 'xp': 75, 'icon': '🧠'},
    'streak_7': {'name': '7-Day Streak', 'xp': 50, 'icon': '🔥'},
}

XP_EVENTS = {
    'resume_upload': 25,
    'placement_predict': 30,
    'interview_complete': 40,
    'skill_gap': 20,
    'roadmap': 25,
    'chat': 10,
    'certificate': 35,
    'profile_complete': 50,
}


def _level_from_xp(xp):
    return max(1, xp // 100 + 1)


def get_or_create_gamification(user_id):
    g = UserGamification.query.filter_by(user_id=user_id).first()
    if not g:
        g = UserGamification(user_id=user_id, badges='[]')
        db.session.add(g)
        db.session.commit()
    return g


def award_xp(user_id, event, badge_key=None):
    g = get_or_create_gamification(user_id)
    xp_gain = XP_EVENTS.get(event, 10)
    g.xp = (g.xp or 0) + xp_gain
    g.leaderboard_points = (g.leaderboard_points or 0) + xp_gain
    g.level = _level_from_xp(g.xp)

    today = datetime.utcnow().strftime('%Y-%m-%d')
    if g.last_activity_date:
        last = datetime.strptime(g.last_activity_date[:10], '%Y-%m-%d')
        diff = (datetime.utcnow().date() - last.date()).days
        if diff == 1:
            g.daily_streak = (g.daily_streak or 0) + 1
        elif diff > 1:
            g.daily_streak = 1
    else:
        g.daily_streak = 1
    g.last_activity_date = today
    if g.daily_streak and g.daily_streak % 7 == 0:
        g.weekly_streak = (g.weekly_streak or 0) + 1

    badges = json.loads(g.badges or '[]')
    if badge_key and badge_key not in badges:
        badges.append(badge_key)
        g.xp += BADGE_DEFS.get(badge_key, {}).get('xp', 0)
    g.badges = json.dumps(badges)
    db.session.commit()
    return g


def get_badges_display(gamification):
    badges = json.loads(gamification.badges or '[]')
    return [BADGE_DEFS.get(b, {'name': b, 'icon': '🏅'}) for b in badges]
