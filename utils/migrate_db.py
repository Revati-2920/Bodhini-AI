"""SQLite migration helper for adding new columns to existing tables."""
import sqlite3
import os


def _get_db_path(app):
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///bodhini.db')
    if uri.startswith('sqlite:///'):
        path = uri.replace('sqlite:///', '')
        if not os.path.isabs(path):
            # Check instance folder first (Flask default), then app root
            instance_path = os.path.join(app.instance_path, os.path.basename(path))
            root_path = os.path.join(app.root_path, path)
            if os.path.exists(instance_path):
                return instance_path
            if os.path.exists(root_path):
                return root_path
            os.makedirs(os.path.dirname(instance_path), exist_ok=True)
            return instance_path
        return path
    return None


def run_migrations(app):
    db_path = _get_db_path(app)
    if not db_path or not os.path.exists(db_path):
        return

    migrations = {
        'user': [
            ('is_admin', 'BOOLEAN DEFAULT 0'),
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('profile_picture', "VARCHAR(255) DEFAULT 'default-avatar.png'"),
            ('college', 'VARCHAR(255)'),
            ('department', 'VARCHAR(255)'),
            ('year', 'VARCHAR(50)'),
            ('cgpa', 'VARCHAR(50)'),
            ('created_at', 'VARCHAR(50)'),
            ('last_login', 'VARCHAR(50)'),
            ('skills', 'TEXT'),
            ('interests', 'TEXT'),
            ('dream_company', 'VARCHAR(255)'),
            ('preferred_domain', 'VARCHAR(255)'),
            ('linkedin', 'VARCHAR(500)'),
            ('github', 'VARCHAR(500)'),
            ('resume_path', 'VARCHAR(500)'),
            ('bio', 'TEXT'),
            ('theme', "VARCHAR(20) DEFAULT 'dark'"),
            ('notify_email', 'BOOLEAN DEFAULT 1'),
            ('notify_push', 'BOOLEAN DEFAULT 1'),
            ('language', "VARCHAR(20) DEFAULT 'en'"),
        ],
        'resume_analysis': [
            ('file_path', 'VARCHAR(500)'),
            ('keyword_match', 'INTEGER'),
            ('formatting_score', 'INTEGER'),
            ('grammar_score', 'INTEGER'),
        ],
        'placement_prediction': [
            ('placement_chance', 'VARCHAR(50)'),
            ('strengths', 'TEXT'),
            ('weaknesses', 'TEXT'),
        ],
        'interview_history': [
            ('questions_data', 'TEXT'),
            ('feedback_data', 'TEXT'),
            ('communication_rating', 'FLOAT'),
            ('technical_rating', 'FLOAT'),
            ('confidence_rating', 'FLOAT'),
        ],
        'skill_gap_analysis': [
            ('recommended_skills', 'TEXT'),
            ('recommended_courses', 'TEXT'),
            ('learning_progress', 'INTEGER DEFAULT 0'),
        ],
        'company': [
            ('interview_questions', 'TEXT'),
            ('coding_questions', 'TEXT'),
            ('preparation_tips', 'TEXT'),
            ('company_resources', 'TEXT'),
        ],
    }

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for table, columns in migrations.items():
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            continue
        cursor.execute(f'PRAGMA table_info({table})')
        existing = {row[1] for row in cursor.fetchall()}
        for col_name, col_type in columns:
            if col_name not in existing:
                try:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}')
                except sqlite3.OperationalError:
                    pass

    conn.commit()
    conn.close()
