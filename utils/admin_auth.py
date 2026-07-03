from functools import wraps
from flask import session, redirect, url_for, flash, request
from database import User


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin.admin_login', next=request.path))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return redirect(url_for('dashboard'))
        if not user.is_active:
            session.clear()
            flash('Your admin account has been disabled.', 'error')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


def get_admin_user():
    if 'user_id' not in session:
        return None
    user = User.query.get(session['user_id'])
    if user and user.is_admin:
        return user
    return None
