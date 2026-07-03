from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    from database import User
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])
