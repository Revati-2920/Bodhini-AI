"""Student-facing premium features blueprint."""
import json
import os
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, current_app, Response,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc

from database import (
    db, User, Company, Event, LearningResource, Bookmark,
    Notification, UserCertificate, Feedback, UserGamification,
    ResumeAnalysis, PlacementPrediction, InterviewHistory,
    SkillGapAnalysis, CareerRoadmap,
)
from utils.student_auth import login_required, get_current_user
from services.career_score import compute_career_scores, progress_chart_data
from services.recommendations import get_recommendations
from services.activity import get_activity_timeline, log_activity
from services.gamification import get_or_create_gamification, get_badges_display, award_xp
from services.notifications import (
    get_notifications, get_unread_count, mark_read, mark_all_read, create_notification,
)
from services.weekly_report import generate_weekly_report
from utils.exports import export_pdf

student_bp = Blueprint('student', __name__)

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC = {'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg'}


def _now():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def _upload(file, subfolder, allowed=None):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if allowed and ext not in allowed:
        return None
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    file.save(os.path.join(upload_dir, filename))
    return f'uploads/{subfolder}/{filename}'


@student_bp.context_processor
def inject_globals():
    if 'user_id' not in session:
        return {}
    return {
        'unread_notifications': get_unread_count(session['user_id']),
        'current_user_obj': get_current_user(),
    }


# ─── Profile ────────────────────────────────────────────────────────────────

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    if request.method == 'POST':
        user.username = request.form.get('username', user.username).strip()
        user.college = request.form.get('college', '')
        user.department = request.form.get('department', '')
        user.year = request.form.get('year', '')
        user.cgpa = request.form.get('cgpa', '')
        user.skills = request.form.get('skills', '')
        user.interests = request.form.get('interests', '')
        user.dream_company = request.form.get('dream_company', '')
        user.preferred_domain = request.form.get('preferred_domain', '')
        user.linkedin = request.form.get('linkedin', '')
        user.github = request.form.get('github', '')
        user.bio = request.form.get('bio', '')
        pic = _upload(request.files.get('profile_picture'), 'avatars', ALLOWED_IMAGE)
        if pic:
            user.profile_picture = pic
        resume = _upload(request.files.get('resume'), 'resumes', ALLOWED_DOC)
        if resume:
            user.resume_path = resume
        db.session.commit()
        award_xp(user.id, 'profile_complete', 'career_explorer')
        log_activity(user.id, 'profile', 'Profile updated')
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))
    gamification = get_or_create_gamification(user.id)
    scores = compute_career_scores(user.id, (
        User, ResumeAnalysis, PlacementPrediction,
        InterviewHistory, SkillGapAnalysis, UserCertificate,
    ))
    return render_template('student/profile.html', user=user, gamification=gamification,
                           scores=scores, badges=get_badges_display(gamification))


# ─── Settings ───────────────────────────────────────────────────────────────

@student_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action', 'general')
        if action == 'password':
            current = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            if check_password_hash(user.password, current) and new_pass:
                user.password = generate_password_hash(new_pass)
                flash('Password changed.', 'success')
            else:
                flash('Current password incorrect.', 'error')
        elif action == 'delete':
            db.session.delete(user)
            session.clear()
            flash('Account deleted.', 'info')
            return redirect(url_for('landing'))
        else:
            user.theme = request.form.get('theme', 'dark')
            user.notify_email = request.form.get('notify_email') == 'on'
            user.notify_push = request.form.get('notify_push') == 'on'
            user.language = request.form.get('language', 'en')
            flash('Settings saved.', 'success')
        db.session.commit()
        return redirect(url_for('student.settings'))
    return render_template('student/settings.html', user=user)


# ─── Companies ──────────────────────────────────────────────────────────────

@student_bp.route('/companies')
@login_required
def companies():
    q = request.args.get('q', '').strip()
    query = Company.query.filter_by(is_active=True).order_by(desc(Company.created_at))
    if q:
        query = query.filter(Company.name.ilike(f'%{q}%'))
    items = query.all()
    bookmarks = {b.item_id for b in Bookmark.query.filter_by(
        user_id=session['user_id'], item_type='company').all()}
    return render_template('student/companies.html', items=items, q=q, bookmarks=bookmarks)


@student_bp.route('/companies/<int:company_id>')
@login_required
def company_detail(company_id):
    company = Company.query.filter_by(id=company_id, is_active=True).first_or_404()
    bookmarked = Bookmark.query.filter_by(
        user_id=session['user_id'], item_type='company', item_id=company_id).first()
    resources = LearningResource.query.filter_by(is_active=True).limit(6).all()
    return render_template('student/company_detail.html', company=company,
                           bookmarked=bool(bookmarked), resources=resources)


# ─── Calendar ───────────────────────────────────────────────────────────────

@student_bp.route('/calendar')
@login_required
def calendar():
    events = Event.query.order_by(Event.event_date).all()
    events_json = [{'title': e.title, 'start': e.event_date, 'type': e.event_type,
                    'venue': e.venue, 'link': e.registration_link, 'status': e.status}
                   for e in events if e.event_date]
    return render_template('student/calendar.html', events=events, events_json=events_json)


# ─── Resources ──────────────────────────────────────────────────────────────

@student_bp.route('/resources')
@login_required
def resources():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    query = LearningResource.query.filter_by(is_active=True).order_by(desc(LearningResource.created_at))
    if q:
        query = query.filter(LearningResource.title.ilike(f'%{q}%'))
    if category:
        query = query.filter_by(category=category)
    items = query.all()
    categories = ['Notes', 'Roadmaps', 'Videos', 'Resume Templates', 'Coding Sheets',
                  'Interview PDFs', 'Aptitude PDFs', 'PDF']
    return render_template('student/resources.html', items=items, q=q,
                           category=category, categories=categories)


# ─── Certificates ───────────────────────────────────────────────────────────

@student_bp.route('/certificates', methods=['GET', 'POST'])
@login_required
def certificates():
    user_id = session['user_id']
    if request.method == 'POST':
        cert = UserCertificate(
            user_id=user_id,
            title=request.form.get('title', ''),
            issuer=request.form.get('issuer', 'Other'),
            category=request.form.get('category', 'Other'),
            earned_at=request.form.get('earned_at', _now()[:10]),
            created_at=_now(),
        )
        fpath = _upload(request.files.get('certificate'), 'certificates', ALLOWED_DOC)
        if fpath:
            cert.file_path = fpath
        db.session.add(cert)
        db.session.commit()
        award_xp(user_id, 'certificate')
        create_notification(user_id, 'Certificate Added', f'"{cert.title}" uploaded successfully.', 'success')
        db.session.commit()
        flash('Certificate uploaded!', 'success')
        return redirect(url_for('student.certificates'))

    certs = UserCertificate.query.filter_by(user_id=user_id).order_by(desc(UserCertificate.created_at)).all()
    issuers = {}
    for c in certs:
        issuers[c.issuer or 'Other'] = issuers.get(c.issuer or 'Other', 0) + 1
    return render_template('student/certificates.html', certificates=certs,
                           issuer_stats=issuers, total=len(certs))


# ─── Weekly Report ──────────────────────────────────────────────────────────

@student_bp.route('/weekly-report')
@login_required
def weekly_report():
    report = generate_weekly_report(session['user_id'])
    return render_template('student/weekly_report.html', report=report)


@student_bp.route('/weekly-report/download')
@login_required
def weekly_report_download():
    report = generate_weekly_report(session['user_id'])
    headers = ['Metric', 'Value']
    rows = [
        ['Overall Career Score', f"{report['scores']['overall']}/100"],
        ['Grade', report['grade']],
        ['Resume Score', report['scores']['resume_score']],
        ['ATS Score', report['scores']['ats_score']],
        ['Placement Score', report['scores']['placement_score']],
        ['Interview Score', report['scores']['interview_score']],
        ['Skill Score', report['scores']['skill_score']],
        ['Resumes This Week', report['resume_improvements']],
        ['Interviews This Week', report['interview_practice']],
        ['Courses Completed', report['courses_completed']],
    ]
    data, fname, mime = export_pdf('weekly_report', 'Bodhini AI - Weekly Report', headers, rows)
    return Response(data, mimetype=mime, headers={'Content-Disposition': f'attachment; filename={fname}'})


# ─── Notifications ──────────────────────────────────────────────────────────

@student_bp.route('/notifications')
@login_required
def notifications_page():
    items = get_notifications(session['user_id'], 50)
    return render_template('student/notifications.html', items=items)


@student_bp.route('/notifications/<int:nid>/read', methods=['POST'])
@login_required
def notification_read(nid):
    mark_read(nid, session['user_id'])
    return redirect(request.referrer or url_for('student.notifications_page'))


@student_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def notifications_read_all():
    mark_all_read(session['user_id'])
    return redirect(url_for('student.notifications_page'))


@student_bp.route('/api/notifications')
@login_required
def api_notifications():
    items = get_notifications(session['user_id'], 10)
    return jsonify([{
        'id': n.id, 'title': n.title, 'message': n.message,
        'type': n.notification_type, 'link': n.link,
        'is_read': n.is_read, 'created_at': n.created_at,
    } for n in items])


# ─── Bookmarks ──────────────────────────────────────────────────────────────

@student_bp.route('/bookmarks')
@login_required
def bookmarks():
    items = Bookmark.query.filter_by(user_id=session['user_id']).order_by(desc(Bookmark.created_at)).all()
    return render_template('student/bookmarks.html', items=items)


@student_bp.route('/bookmarks/toggle', methods=['POST'])
@login_required
def bookmark_toggle():
    item_type = request.form.get('item_type')
    item_id = int(request.form.get('item_id', 0))
    title = request.form.get('title', '')
    existing = Bookmark.query.filter_by(
        user_id=session['user_id'], item_type=item_type, item_id=item_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'bookmarked': False})
        flash('Bookmark removed.', 'info')
        return redirect(request.referrer or url_for('student.bookmarks'))
    b = Bookmark(user_id=session['user_id'], item_type=item_type,
                 item_id=item_id, title=title, created_at=_now())
    db.session.add(b)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'bookmarked': True})
    flash('Bookmarked!', 'success')
    return redirect(request.referrer or url_for('student.bookmarks'))


# ─── Leaderboard ────────────────────────────────────────────────────────────

@student_bp.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.filter_by(is_admin=False, is_active=True).all()
    ranked = []
    for u in users:
        scores = compute_career_scores(u.id, (
            User, ResumeAnalysis, PlacementPrediction,
            InterviewHistory, SkillGapAnalysis, UserCertificate,
        ))
        g = UserGamification.query.filter_by(user_id=u.id).first()
        ranked.append({
            'user': u,
            'scores': scores,
            'xp': g.xp if g else 0,
            'level': g.level if g else 1,
        })
    ranked.sort(key=lambda x: x['scores']['overall'], reverse=True)
    return render_template('student/leaderboard.html', ranked=ranked[:50])


# ─── Support ─────────────────────────────────────────────────────────────────

@student_bp.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        user_id = session.get('user_id')
        fb = Feedback(
            user_id=user_id,
            module='support',
            rating=int(request.form.get('rating', 5)),
            feedback_text=request.form.get('message', ''),
            suggestions=request.form.get('subject', ''),
            created_at=_now(),
        )
        db.session.add(fb)
        db.session.commit()
        flash('Message sent! We will respond within 24 hours.', 'success')
        return redirect(url_for('student.support'))
    return render_template('student/support.html')


# ─── Feedback (module-level) ─────────────────────────────────────────────────

@student_bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    fb = Feedback(
        user_id=session['user_id'],
        module=request.form.get('module', 'general'),
        rating=int(request.form.get('rating', 5)),
        feedback_text=request.form.get('feedback', ''),
        suggestions=request.form.get('suggestions', ''),
        issue_report=request.form.get('issue', ''),
        created_at=_now(),
    )
    db.session.add(fb)
    db.session.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(request.referrer or url_for('dashboard'))


# ─── PDF Exports ─────────────────────────────────────────────────────────────

@student_bp.route('/export/<report_type>/<int:item_id>')
@login_required
def export_report(report_type, item_id):
    user_id = session['user_id']
    title = 'Bodhini AI Report'
    headers = ['Field', 'Value']
    rows = []

    if report_type == 'resume' or report_type == 'ats':
        item = ResumeAnalysis.query.filter_by(id=item_id, user_id=user_id).first_or_404()
        title = 'Bodhini AI - ATS Resume Report'
        rows = [['Resume', item.resume_name or ''], ['ATS Score', f'{item.ats_score}%'],
                ['Resume Score', item.resume_score], ['Date', item.created_at or '']]
    elif report_type == 'placement':
        item = PlacementPrediction.query.filter_by(id=item_id, user_id=user_id).first_or_404()
        title = 'Bodhini AI - Placement Report'
        rows = [['Student', item.student_name or ''], ['Score', f'{item.prediction_score}%'],
                ['Package', item.expected_package or ''], ['Date', item.created_at or '']]
    elif report_type == 'interview':
        item = InterviewHistory.query.filter_by(id=item_id, user_id=user_id).first_or_404()
        title = 'Bodhini AI - Interview Report'
        rows = [['Type', item.interview_type or ''], ['Score', f'{item.overall_score}/10'],
                ['Questions', item.total_questions], ['Date', item.created_at or '']]
    elif report_type == 'skill-gap':
        item = SkillGapAnalysis.query.filter_by(id=item_id, user_id=user_id).first_or_404()
        title = 'Bodhini AI - Skill Gap Report'
        rows = [['Career Goal', item.career_goal or ''], ['Match', f'{item.skill_match}%'],
                ['Date', item.created_at or '']]
    elif report_type == 'roadmap':
        item = CareerRoadmap.query.filter_by(id=item_id, user_id=user_id).first_or_404()
        title = 'Bodhini AI - Career Roadmap'
        rows = [['Goal', item.career_goal or ''], ['Education', item.education or ''],
                ['Date', item.created_at or '']]
    elif report_type == 'career-score':
        scores = compute_career_scores(user_id, (
            User, ResumeAnalysis, PlacementPrediction,
            InterviewHistory, SkillGapAnalysis, UserCertificate,
        ))
        title = 'Bodhini AI - Career Score'
        rows = [[k.replace('_', ' ').title(), v] for k, v in scores.items() if k != 'grade']
        rows.append(['Grade', scores['grade']])
    else:
        return redirect(url_for('dashboard'))

    data, fname, mime = export_pdf(report_type, title, headers, rows)
    return Response(data, mimetype=mime, headers={'Content-Disposition': f'attachment; filename={fname}'})
