"""Notification helpers."""
from datetime import datetime
from database import db, Notification


def create_notification(user_id, title, message, notification_type='info', link=None):
    n = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        is_read=False,
        created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
    )
    db.session.add(n)
    return n


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_notifications(user_id, limit=20):
    return Notification.query.filter_by(user_id=user_id).order_by(
        Notification.created_at.desc()
    ).limit(limit).all()


def mark_read(notification_id, user_id):
    n = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if n:
        n.is_read = True
        db.session.commit()
    return n


def mark_all_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
