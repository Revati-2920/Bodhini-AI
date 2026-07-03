"""Premium Admin Panel routes for Bodhini AI."""
import json
import os
import shutil
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, current_app, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc, asc

from database import (
    db, User, ResumeAnalysis, PlacementPrediction,
    InterviewHistory, SkillGapAnalysis, AIChatLog,
    Company, Event, LearningResource, Announcement, AdminSettings,
)
from utils.admin_auth import admin_required, get_admin_user
from utils.exports import export_csv, export_excel, export_pdf
from routes.admin_helpers import (
    now_str, paginate, apply_sort, get_settings,
    get_analytics, chart_data, user_search_query,
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOC = {'pdf', 'docx', 'doc', 'ppt', 'pptx', 'mp4', 'zip'}


def _upload(file, subfolder, allowed=None):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if allowed and ext not in allowed:
        return None
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    path = os.path.join(upload_dir, filename)
    file.save(path)
    return f'uploads/{subfolder}/{filename}'


# ─── Auth ───────────────────────────────────────────────────────────────────

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if get_admin_user():
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter(
            or_(User.email.ilike(email), User.username.ilike(email))
        ).first()
        if user and user.is_admin and user.is_active and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = True
            user.last_login = now_str()
            db.session.commit()
            flash('Welcome back, Admin!', 'success')
            nxt = request.args.get('next') or url_for('admin.dashboard')
            return redirect(nxt)
        flash('Invalid admin credentials or access denied.', 'error')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/')
@admin_required
def dashboard():
    stats = get_analytics()
    charts = chart_data()
    return render_template('admin/dashboard.html', stats=stats, charts=charts)


# ─── Users ──────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users_list():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    department = request.args.get('department', '').strip()
    sort_by = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = user_search_query(q, status, department)
    query = apply_sort(query, User, sort_by, order, ['id', 'username', 'email', 'created_at', 'last_login'])
    users, total, page, per_page, pages = paginate(query, page, per_page)
    return render_template('admin/users.html', users=users, total=total, page=page,
                           per_page=per_page, pages=pages, q=q, status=status,
                           department=department, sort=sort_by, order=order)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_view(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(404)
    return render_template('admin/user_view.html', user=user)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(404)
    if request.method == 'POST':
        user.username = request.form.get('username', user.username)
        user.email = request.form.get('email', user.email)
        user.college = request.form.get('college', '')
        user.department = request.form.get('department', '')
        user.year = request.form.get('year', '')
        user.cgpa = request.form.get('cgpa', '')
        user.is_active = request.form.get('is_active') == 'on'
        pic = _upload(request.files.get('profile_picture'), 'avatars', ALLOWED_IMAGE)
        if pic:
            user.profile_picture = pic
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.users_list'))
    return render_template('admin/user_edit.html', user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete admin accounts.', 'error')
        return redirect(url_for('admin.users_list'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"Account {'enabled' if user.is_active else 'disabled'}.", 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def user_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', 'Bodhini@123')
    user.password = generate_password_hash(new_pass)
    db.session.commit()
    flash('Password reset successfully.', 'success')
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/export/<fmt>')
@admin_required
def users_export(fmt):
    users = User.query.filter_by(is_admin=False).all()
    headers = ['ID', 'Name', 'Email', 'College', 'Department', 'Year', 'CGPA', 'Status', 'Registered', 'Last Login']
    rows = [[u.id, u.username, u.email, u.college or '', u.department or '', u.year or '',
             u.cgpa or '', 'Active' if u.is_active else 'Disabled', u.created_at or '', u.last_login or '']
            for u in users]
    return _send_export(fmt, 'users', 'Bodhini AI - Users', headers, rows)


# ─── Resumes ────────────────────────────────────────────────────────────────

@admin_bp.route('/resumes')
@admin_required
def resumes_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = ResumeAnalysis.query.join(User).order_by(desc(ResumeAnalysis.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(ResumeAnalysis.resume_name.ilike(like), User.username.ilike(like)))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/resumes.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


@admin_bp.route('/resumes/<int:item_id>/delete', methods=['POST'])
@admin_required
def resume_delete(item_id):
    item = ResumeAnalysis.query.get_or_404(item_id)
    if item.file_path:
        fp = os.path.join(current_app.root_path, 'static', item.file_path)
        if os.path.exists(fp):
            os.remove(fp)
    db.session.delete(item)
    db.session.commit()
    flash('Resume deleted.', 'success')
    return redirect(url_for('admin.resumes_list'))


@admin_bp.route('/resumes/<int:item_id>/download')
@admin_required
def resume_download(item_id):
    item = ResumeAnalysis.query.get_or_404(item_id)
    if item.file_path:
        fp = os.path.join(current_app.root_path, 'static', item.file_path)
        if os.path.exists(fp):
            return send_file(fp, as_attachment=True, download_name=item.resume_name or 'resume.pdf')
    abort(404)


# ─── ATS Reports ────────────────────────────────────────────────────────────

@admin_bp.route('/ats-reports')
@admin_required
def ats_reports():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = ResumeAnalysis.query.join(User).order_by(desc(ResumeAnalysis.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(User.username.ilike(like), ResumeAnalysis.resume_name.ilike(like)))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/ats_reports.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


@admin_bp.route('/ats-reports/<int:item_id>')
@admin_required
def ats_report_view(item_id):
    item = ResumeAnalysis.query.get_or_404(item_id)
    report = {}
    try:
        report = json.loads(item.feedback) if item.feedback else {}
    except Exception:
        report = {}
    return render_template('admin/ats_report_view.html', item=item, report=report)


# ─── Placements ─────────────────────────────────────────────────────────────

@admin_bp.route('/placements')
@admin_required
def placements_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = PlacementPrediction.query.join(User).order_by(desc(PlacementPrediction.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(PlacementPrediction.student_name.ilike(like), User.username.ilike(like)))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/placements.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


# ─── Interviews ───────────────────────────────────────────────────────────────

@admin_bp.route('/interviews')
@admin_required
def interviews_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = InterviewHistory.query.join(User).order_by(desc(InterviewHistory.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(User.username.ilike(like), InterviewHistory.interview_type.ilike(like)))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/interviews.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


# ─── Skill Gaps ───────────────────────────────────────────────────────────────

@admin_bp.route('/skill-gaps')
@admin_required
def skill_gaps_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = SkillGapAnalysis.query.join(User).order_by(desc(SkillGapAnalysis.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(User.username.ilike(like), SkillGapAnalysis.career_goal.ilike(like)))
    items, total, page, per_page, pages = paginate(query, page)
    charts = chart_data()
    return render_template('admin/skill_gaps.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q, charts=charts)


# ─── Chat Logs ────────────────────────────────────────────────────────────────

@admin_bp.route('/chat-logs')
@admin_required
def chat_logs():
    q = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = request.args.get('page', 1, type=int)
    query = AIChatLog.query.join(User).order_by(desc(AIChatLog.created_at))
    if q:
        like = f'%{q}%'
        query = query.filter(or_(AIChatLog.prompt.ilike(like), User.username.ilike(like)))
    if date_from:
        query = query.filter(AIChatLog.created_at >= date_from)
    if date_to:
        query = query.filter(AIChatLog.created_at <= date_to + ' 23:59:59')
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/chat_logs.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q, date_from=date_from, date_to=date_to)


@admin_bp.route('/chat-logs/export/<fmt>')
@admin_required
def chat_logs_export(fmt):
    logs = AIChatLog.query.order_by(desc(AIChatLog.created_at)).all()
    headers = ['ID', 'User', 'Prompt', 'Response', 'Module', 'Date']
    rows = [[l.id, l.user.username if l.user else '', (l.prompt or '')[:100],
             (l.response or '')[:100], l.module_used, l.created_at] for l in logs]
    return _send_export(fmt, 'chat_logs', 'Bodhini AI - Chat Logs', headers, rows)


# ─── Companies CRUD ───────────────────────────────────────────────────────────

@admin_bp.route('/companies')
@admin_required
def companies_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Company.query.order_by(desc(Company.created_at))
    if q:
        query = query.filter(Company.name.ilike(f'%{q}%'))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/companies.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


@admin_bp.route('/companies/add', methods=['GET', 'POST'])
@admin_bp.route('/companies/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def company_form(item_id=None):
    item = Company.query.get(item_id) if item_id else None
    if request.method == 'POST':
        if not item:
            item = Company(created_at=now_str())
        item.name = request.form.get('name', '')
        item.package = request.form.get('package', '')
        item.location = request.form.get('location', '')
        item.eligibility = request.form.get('eligibility', '')
        item.required_skills = request.form.get('required_skills', '')
        item.application_deadline = request.form.get('application_deadline', '')
        item.official_website = request.form.get('official_website', '')
        item.selection_process = request.form.get('selection_process', '')
        item.is_active = request.form.get('is_active') == 'on'
        logo = _upload(request.files.get('logo'), 'companies', ALLOWED_IMAGE)
        if logo:
            item.logo = logo
        if not item_id:
            db.session.add(item)
        db.session.commit()
        flash('Company saved.', 'success')
        return redirect(url_for('admin.companies_list'))
    return render_template('admin/company_form.html', item=item)


@admin_bp.route('/companies/<int:item_id>/delete', methods=['POST'])
@admin_required
def company_delete(item_id):
    item = Company.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Company deleted.', 'success')
    return redirect(url_for('admin.companies_list'))


# ─── Events CRUD ──────────────────────────────────────────────────────────────

@admin_bp.route('/events')
@admin_required
def events_list():
    q = request.args.get('q', '').strip()
    event_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    query = Event.query.order_by(desc(Event.event_date))
    if q:
        query = query.filter(Event.title.ilike(f'%{q}%'))
    if event_type:
        query = query.filter_by(event_type=event_type)
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/events.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q, event_type=event_type)


@admin_bp.route('/events/add', methods=['GET', 'POST'])
@admin_bp.route('/events/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def event_form(item_id=None):
    item = Event.query.get(item_id) if item_id else None
    if request.method == 'POST':
        if not item:
            item = Event(created_at=now_str())
        item.title = request.form.get('title', '')
        item.description = request.form.get('description', '')
        item.event_type = request.form.get('event_type', 'Workshop')
        item.event_date = request.form.get('event_date', '')
        item.venue = request.form.get('venue', '')
        item.registration_link = request.form.get('registration_link', '')
        item.status = request.form.get('status', 'Upcoming')
        poster = _upload(request.files.get('poster'), 'events', ALLOWED_IMAGE)
        if poster:
            item.poster = poster
        if not item_id:
            db.session.add(item)
        db.session.commit()
        flash('Event saved.', 'success')
        return redirect(url_for('admin.events_list'))
    return render_template('admin/event_form.html', item=item)


@admin_bp.route('/events/<int:item_id>/delete', methods=['POST'])
@admin_required
def event_delete(item_id):
    item = Event.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Event deleted.', 'success')
    return redirect(url_for('admin.events_list'))


# ─── Learning Resources CRUD ──────────────────────────────────────────────────

@admin_bp.route('/resources')
@admin_required
def resources_list():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    query = LearningResource.query.order_by(desc(LearningResource.created_at))
    if q:
        query = query.filter(LearningResource.title.ilike(f'%{q}%'))
    if category:
        query = query.filter_by(category=category)
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/resources.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q, category=category)


@admin_bp.route('/resources/add', methods=['GET', 'POST'])
@admin_bp.route('/resources/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def resource_form(item_id=None):
    item = LearningResource.query.get(item_id) if item_id else None
    if request.method == 'POST':
        if not item:
            item = LearningResource(created_at=now_str())
        item.title = request.form.get('title', '')
        item.description = request.form.get('description', '')
        item.category = request.form.get('category', 'Notes')
        item.resource_type = request.form.get('resource_type', 'PDF')
        item.external_url = request.form.get('external_url', '')
        item.is_active = request.form.get('is_active') == 'on'
        fpath = _upload(request.files.get('file'), 'resources', ALLOWED_DOC | ALLOWED_IMAGE)
        if fpath:
            item.file_path = fpath
        if not item_id:
            db.session.add(item)
        db.session.commit()
        flash('Resource saved.', 'success')
        return redirect(url_for('admin.resources_list'))
    return render_template('admin/resource_form.html', item=item)


@admin_bp.route('/resources/<int:item_id>/delete', methods=['POST'])
@admin_required
def resource_delete(item_id):
    item = LearningResource.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Resource deleted.', 'success')
    return redirect(url_for('admin.resources_list'))


# ─── Announcements CRUD ───────────────────────────────────────────────────────

@admin_bp.route('/announcements')
@admin_required
def announcements_list():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    query = Announcement.query.order_by(desc(Announcement.created_at))
    if q:
        query = query.filter(Announcement.title.ilike(f'%{q}%'))
    items, total, page, per_page, pages = paginate(query, page)
    return render_template('admin/announcements.html', items=items, total=total, page=page,
                           per_page=per_page, pages=pages, q=q)


@admin_bp.route('/announcements/add', methods=['GET', 'POST'])
@admin_bp.route('/announcements/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def announcement_form(item_id=None):
    item = Announcement.query.get(item_id) if item_id else None
    if request.method == 'POST':
        if not item:
            item = Announcement(created_at=now_str())
        item.title = request.form.get('title', '')
        item.description = request.form.get('description', '')
        item.priority = request.form.get('priority', 'Normal')
        item.expiry_date = request.form.get('expiry_date', '')
        item.is_active = request.form.get('is_active') == 'on'
        img = _upload(request.files.get('image'), 'announcements', ALLOWED_IMAGE)
        if img:
            item.image = img
        if not item_id:
            db.session.add(item)
        db.session.commit()
        flash('Announcement published.', 'success')
        return redirect(url_for('admin.announcements_list'))
    return render_template('admin/announcement_form.html', item=item)


@admin_bp.route('/announcements/<int:item_id>/delete', methods=['POST'])
@admin_required
def announcement_delete(item_id):
    item = Announcement.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('admin.announcements_list'))


# ─── Settings ─────────────────────────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    settings_obj = get_settings()
    admin_user = get_admin_user()
    if request.method == 'POST':
        action = request.form.get('action', 'general')
        if action == 'profile':
            admin_user.username = request.form.get('username', admin_user.username)
            admin_user.email = request.form.get('email', admin_user.email)
            pic = _upload(request.files.get('profile_picture'), 'avatars', ALLOWED_IMAGE)
            if pic:
                admin_user.profile_picture = pic
            flash('Profile updated.', 'success')
        elif action == 'password':
            current = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            if check_password_hash(admin_user.password, current) and new_pass:
                admin_user.password = generate_password_hash(new_pass)
                flash('Password changed.', 'success')
            else:
                flash('Current password incorrect.', 'error')
        elif action == 'general':
            settings_obj.website_name = request.form.get('website_name', settings_obj.website_name)
            settings_obj.ai_api_key = request.form.get('ai_api_key', '')
            settings_obj.theme_primary = request.form.get('theme_primary', '#2563eb')
            settings_obj.theme_secondary = request.form.get('theme_secondary', '#4f46e5')
            logo = _upload(request.files.get('logo'), 'branding', ALLOWED_IMAGE)
            if logo:
                settings_obj.logo_path = logo
            settings_obj.updated_at = now_str()
            flash('Settings saved.', 'success')
        elif action == 'email':
            settings_obj.smtp_host = request.form.get('smtp_host', '')
            settings_obj.smtp_port = request.form.get('smtp_port', '')
            settings_obj.smtp_email = request.form.get('smtp_email', '')
            settings_obj.smtp_password = request.form.get('smtp_password', '')
            settings_obj.updated_at = now_str()
            flash('Email settings saved.', 'success')
        elif action == 'backup':
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(current_app.root_path, db_path)
            if os.path.exists(db_path):
                backup_dir = os.path.join(current_app.root_path, 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                dest = os.path.join(backup_dir, f"bodhini_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                shutil.copy2(db_path, dest)
                flash(f'Database backed up to {os.path.basename(dest)}.', 'success')
            else:
                flash('Database file not found.', 'error')
        elif action == 'restore':
            restore_file = request.files.get('restore_file')
            if restore_file and restore_file.filename.endswith('.db'):
                db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
                if not os.path.isabs(db_path):
                    db_path = os.path.join(current_app.root_path, db_path)
                restore_file.save(db_path)
                flash('Database restored. Restart the app.', 'warning')
        db.session.commit()
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', settings=settings_obj, admin_user=admin_user)


# ─── Export helper ────────────────────────────────────────────────────────────

def _send_export(fmt, filename, title, headers, rows):
    from flask import Response
    if fmt == 'csv':
        data, fname, mime = export_csv(filename, headers, rows)
        return Response(data, mimetype=mime, headers={'Content-Disposition': f'attachment; filename={fname}'})
    if fmt == 'excel':
        data, fname, mime = export_excel(filename, headers, rows)
        return Response(data, mimetype=mime, headers={'Content-Disposition': f'attachment; filename={fname}'})
    if fmt == 'pdf':
        data, fname, mime = export_pdf(filename, title, headers, rows)
        return Response(data, mimetype=mime, headers={'Content-Disposition': f'attachment; filename={fname}'})
    abort(404)
