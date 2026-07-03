from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    profile_picture = db.Column(db.String(255), default='default-avatar.png')
    college = db.Column(db.String(255))
    department = db.Column(db.String(255))
    year = db.Column(db.String(50))
    cgpa = db.Column(db.String(50))
    skills = db.Column(db.Text)
    interests = db.Column(db.Text)
    dream_company = db.Column(db.String(255))
    preferred_domain = db.Column(db.String(255))
    linkedin = db.Column(db.String(500))
    github = db.Column(db.String(500))
    resume_path = db.Column(db.String(500))
    bio = db.Column(db.Text)
    theme = db.Column(db.String(20), default='dark')
    notify_email = db.Column(db.Boolean, default=True)
    notify_push = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(20), default='en')
    created_at = db.Column(db.String(50))
    last_login = db.Column(db.String(50))

    resume_analyses = db.relationship('ResumeAnalysis', backref='user', lazy='dynamic')
    placement_predictions = db.relationship('PlacementPrediction', backref='user', lazy='dynamic')
    interview_histories = db.relationship('InterviewHistory', backref='user', lazy='dynamic')
    skill_gap_analyses = db.relationship('SkillGapAnalysis', backref='user', lazy='dynamic')
    chat_logs = db.relationship('AIChatLog', backref='user', lazy='dynamic')


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company = db.Column(db.String(100))
    prediction_score = db.Column(db.Float)
    status = db.Column(db.String(20))
    created_at = db.Column(db.String(50))


class ResumeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_score = db.Column(db.Integer)
    ats_score = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    resume_name = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    keyword_match = db.Column(db.Integer)
    formatting_score = db.Column(db.Integer)
    grammar_score = db.Column(db.Integer)
    created_at = db.Column(db.String(50))


class PlacementPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(255))
    college = db.Column(db.String(255))
    branch = db.Column(db.String(255))
    cgpa = db.Column(db.String(50))
    prediction_score = db.Column(db.Integer)
    expected_package = db.Column(db.String(100))
    placement_chance = db.Column(db.String(50))
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    career_advice = db.Column(db.Text)
    timeline = db.Column(db.Text)
    daily_tasks = db.Column(db.Text)
    created_at = db.Column(db.String(50))


class CareerRoadmap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    career_goal = db.Column(db.String(255))
    education = db.Column(db.String(255))
    current_year = db.Column(db.String(255))
    skill_level = db.Column(db.String(255))
    study_time = db.Column(db.String(255))
    learning_style = db.Column(db.String(255))
    roadmap_data = db.Column(db.Text)
    created_at = db.Column(db.String(50))


class InterviewHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interview_type = db.Column(db.String(100))
    company = db.Column(db.String(255))
    difficulty = db.Column(db.String(50))
    overall_score = db.Column(db.Float)
    total_questions = db.Column(db.Integer)
    average_feedback = db.Column(db.String(255))
    questions_data = db.Column(db.Text)
    feedback_data = db.Column(db.Text)
    communication_rating = db.Column(db.Float)
    technical_rating = db.Column(db.Float)
    confidence_rating = db.Column(db.Float)
    created_at = db.Column(db.String(50))


class SkillGapAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    career_goal = db.Column(db.String(255))
    current_skills = db.Column(db.Text)
    skill_match = db.Column(db.Integer)
    missing_skills = db.Column(db.Text)
    recommended_skills = db.Column(db.Text)
    recommended_courses = db.Column(db.Text)
    learning_progress = db.Column(db.Integer, default=0)
    roadmap = db.Column(db.Text)
    created_at = db.Column(db.String(50))


class AIChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    module_used = db.Column(db.String(100), default='AI Career Chat')
    created_at = db.Column(db.String(50))


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    logo = db.Column(db.String(500))
    package = db.Column(db.String(100))
    location = db.Column(db.String(255))
    eligibility = db.Column(db.Text)
    required_skills = db.Column(db.Text)
    application_deadline = db.Column(db.String(50))
    official_website = db.Column(db.String(500))
    selection_process = db.Column(db.Text)
    interview_questions = db.Column(db.Text)
    coding_questions = db.Column(db.Text)
    preparation_tips = db.Column(db.Text)
    company_resources = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String(50))


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(100))
    event_date = db.Column(db.String(50))
    venue = db.Column(db.String(255))
    registration_link = db.Column(db.String(500))
    poster = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Upcoming')
    created_at = db.Column(db.String(50))


class LearningResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    resource_type = db.Column(db.String(50))
    file_path = db.Column(db.String(500))
    external_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String(50))


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(50), default='Normal')
    image = db.Column(db.String(500))
    expiry_date = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String(50))


class AdminSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    website_name = db.Column(db.String(255), default='Bodhini AI')
    logo_path = db.Column(db.String(500), default='images/logo.png')
    ai_api_key = db.Column(db.String(500))
    smtp_host = db.Column(db.String(255))
    smtp_port = db.Column(db.String(20))
    smtp_email = db.Column(db.String(255))
    smtp_password = db.Column(db.String(500))
    theme_primary = db.Column(db.String(20), default='#2563eb')
    theme_secondary = db.Column(db.String(20), default='#4f46e5')
    updated_at = db.Column(db.String(50))


class UserGamification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    badges = db.Column(db.Text, default='[]')
    daily_streak = db.Column(db.Integer, default=0)
    weekly_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.String(50))
    leaderboard_points = db.Column(db.Integer, default=0)


class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255))
    created_at = db.Column(db.String(50))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    notification_type = db.Column(db.String(50))
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.String(50))


class UserCertificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    issuer = db.Column(db.String(100))
    category = db.Column(db.String(100))
    file_path = db.Column(db.String(500))
    earned_at = db.Column(db.String(50))
    created_at = db.Column(db.String(50))


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module = db.Column(db.String(100))
    rating = db.Column(db.Integer)
    feedback_text = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    issue_report = db.Column(db.Text)
    created_at = db.Column(db.String(50))


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    meta_json = db.Column(db.Text)
    created_at = db.Column(db.String(50))
