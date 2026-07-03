#!/usr/bin/env python
"""Create the first admin user for Bodhini AI."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db, User
from werkzeug.security import generate_password_hash
from datetime import datetime


def create_admin(username='admin', email='admin@bodhini.ai', password='Admin@123'):
    with app.app_context():
        existing = User.query.filter_by(email=email).first()
        if existing:
            existing.is_admin = True
            existing.password = generate_password_hash(password)
            print(f'Updated existing user "{email}" to admin.')
        else:
            admin = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                is_admin=True,
                is_active=True,
                created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            )
            db.session.add(admin)
            print(f'Created admin user: {email}')
        db.session.commit()
        print(f'Password: {password}')
        print('Login at: http://127.0.0.1:5000/admin/login')


if __name__ == '__main__':
    create_admin()
