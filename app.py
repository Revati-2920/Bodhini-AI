import json
import os
import re
import shutil
from datetime import datetime

from dotenv import load_dotenv
from groq import Groq
from flask import Flask, render_template, request, redirect, session, url_for, flash

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

from database import (
    db,
    User,
    Prediction,
    ResumeAnalysis,
    PlacementPrediction,
    CareerRoadmap,
    InterviewHistory,
    SkillGapAnalysis,
    AIChatLog,
    Announcement,
)
from routes.admin import admin_bp
from routes.student import student_bp
from utils.migrate_db import run_migrations
from services.career_score import compute_career_scores, progress_chart_data
from services.recommendations import get_recommendations
from services.activity import get_activity_timeline, log_activity
from services.gamification import get_or_create_gamification, get_badges_display, award_xp
from services.notifications import create_notification
from database import UserCertificate

from resume_analyzer import (
    extract_text_from_file,
    parse_resume_analysis,
    analyze_resume,
    build_premium_ats_report
)

from placement_predictor import analyze_profile
from career_roadmap import generate_roadmap

# =========================
# Flask App
# =========================

SYSTEM_PROMPT = """You are Bodhini AI Interview Coach. Conduct professional mock interviews. Ask one question at a time. After each answer provide detailed feedback, score out of 10, strengths, improvements, better answer, and then ask the next interview question."""

app = Flask(__name__)

app.config['SECRET_KEY'] = 'bodhini_secret_key'
_instance_db = os.path.join(os.path.dirname(__file__), 'instance', 'bodhini.db')
os.makedirs(os.path.dirname(_instance_db), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + _instance_db.replace('\\', '/')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# =========================
# Load Environment Variables
# =========================

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

print("GROQ KEY FOUND:", bool(groq_api_key))

client = None

if groq_api_key:
    client = Groq(
        api_key=groq_api_key
    )

# =========================
# Helper Functions
# =========================

def _clean_json_payload(raw_text):
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        try:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start:end + 1])
        except Exception:
            return None


def _generate_interview_question(interview_type, difficulty, target_company, conversation_history):
    if client is None:
        return {
            "question": "Tell me about yourself and why you are a good fit for this role.",
            "focus_area": "Self-introduction",
            "expected_answer_hint": "Mention education, projects, strengths, career goals."
        }

    prompt = f"""
You are Bodhini AI Interview Coach.
Create the next interview question for a {difficulty} {interview_type} interview.
Target company: {target_company or 'any top company'}.
Avoid repeating prior questions.
Use the previous conversation context below.
Conversation history:
{conversation_history}
Return valid JSON with keys: question, focus_area, expected_answer_hint.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        payload = _clean_json_payload(response.choices[0].message.content)
        if payload:
            return payload
    except Exception:
        pass

    return {
        "question": f"Describe one project you are proud of for a {interview_type.lower()} interview.",
        "focus_area": "Project explanation",
        "expected_answer_hint": "Use STAR, mention impact, role, and results."
    }


def _generate_interview_feedback(interview_type, difficulty, target_company, conversation_history, user_answer):
    if client is None:
        return {
            "overall_score": 7.5,
            "communication": 7.5,
            "confidence": 7.0,
            "technical_accuracy": 7.5,
            "grammar": 8.0,
            "professionalism": 8.0,
            "body_language_tips": ["Maintain steady eye contact", "Keep your posture open"],
            "star_method_usage": "Good structure. Add more measurable results.",
            "strengths": ["Clear communication", "Good initiative"],
            "weaknesses": ["Use more examples", "Reduce filler words"],
            "improved_sample_answer": "I have worked on ...",
            "next_question": "Can you explain a challenging problem you solved recently?"
        }

    prompt = f"""
You are an expert interviewer coaching a student for a {difficulty} {interview_type} interview.
Target company: {target_company or 'any top company'}.
The candidate answer was:
{user_answer}
Conversation history:
{conversation_history}
Return valid JSON with exactly these keys:
overall_score, communication, confidence, technical_accuracy, grammar, professionalism, body_language_tips, star_method_usage, strengths, weaknesses, improved_sample_answer, next_question.
Use numeric scores out of 10. body_language_tips and strengths and weaknesses should be arrays.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=900
        )
        payload = _clean_json_payload(response.choices[0].message.content)
        if payload:
            return payload
    except Exception:
        pass

    return {
        "overall_score": 7.5,
        "communication": 7.5,
        "confidence": 7.0,
        "technical_accuracy": 7.5,
        "grammar": 8.0,
        "professionalism": 8.0,
        "body_language_tips": ["Maintain steady eye contact", "Keep your posture open"],
        "star_method_usage": "Good structure. Add more measurable results.",
        "strengths": ["Clear communication", "Good initiative"],
        "weaknesses": ["Use more examples", "Reduce filler words"],
        "improved_sample_answer": "I have worked on ...",
        "next_question": "Can you explain a challenging problem you solved recently?"
    }


def _generate_interview_summary(interview_type, difficulty, target_company, conversation_history):
    if client is None:
        return {
            "overall_score": 8.0,
            "confidence": 7.8,
            "technical_knowledge": 8.0,
            "communication": 8.1,
            "hr_skills": 7.9,
            "problem_solving": 8.2,
            "grammar": 8.3,
            "professionalism": 8.4,
            "strengths": ["Structured responses", "Good confidence"],
            "improvements": ["Use STAR more clearly", "Add stronger examples"],
            "suggestions": ["Practice 3 mock interviews weekly", "Review core technical concepts"],
            "next_steps": ["Read one behavioral interview guide", "Solve one coding challenge daily"]
        }

    prompt = f"""
Summarize this completed mock interview for a {difficulty} {interview_type} interview at {target_company or 'a top company'}.
Conversation history:
{conversation_history}
Return valid JSON with keys: overall_score, confidence, technical_knowledge, communication, hr_skills, problem_solving, grammar, professionalism, strengths, improvements, suggestions, next_steps.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=900
        )
        payload = _clean_json_payload(response.choices[0].message.content)
        if payload:
            return payload
    except Exception:
        pass

    return {
        "overall_score": 8.0,
        "confidence": 7.8,
        "technical_knowledge": 8.0,
        "communication": 8.1,
        "hr_skills": 7.9,
        "problem_solving": 8.2,
        "grammar": 8.3,
        "professionalism": 8.4,
        "strengths": ["Structured responses", "Good confidence"],
        "improvements": ["Use STAR more clearly", "Add stronger examples"],
        "suggestions": ["Practice 3 mock interviews weekly", "Review core technical concepts"],
        "next_steps": ["Read one behavioral interview guide", "Solve one coding challenge daily"]
    }


def _serialize_conversation(conversation):
    return json.dumps(conversation)


def _generate_skill_gap_report(form_data):
    current_skills = [skill.strip() for skill in form_data.get('current_skills', '').splitlines() if skill.strip()]
    if not current_skills:
        current_skills = ['Python', 'SQL', 'HTML', 'CSS']

    default_report = {
        'career_goal': form_data.get('career_goal', 'Software Engineer'),
        'skill_match': 72,
        'readiness_status': 'Needs Improvement',
        'strengths': current_skills[:4],
        'missing_skills': ['Docker', 'REST APIs', 'AWS', 'System Design', 'DSA'],
        'priority_learning': [
            {'skill': 'Data Structures', 'timeline': '3 Weeks'},
            {'skill': 'REST APIs', 'timeline': '2 Weeks'},
            {'skill': 'Docker', 'timeline': '2 Weeks'},
            {'skill': 'AWS Basics', 'timeline': '3 Weeks'},
            {'skill': 'System Design', 'timeline': '4 Weeks'}
        ],
        'skill_gap_table': [
            {'skill': 'Data Structures', 'current': 'Intermediate', 'required': 'Advanced', 'gap': 'High', 'priority': 'High'},
            {'skill': 'REST APIs', 'current': 'Beginner', 'required': 'Intermediate', 'gap': 'Medium', 'priority': 'High'},
            {'skill': 'Docker', 'current': 'Beginner', 'required': 'Intermediate', 'gap': 'Medium', 'priority': 'High'},
            {'skill': 'AWS', 'current': 'Beginner', 'required': 'Intermediate', 'gap': 'High', 'priority': 'High'}
        ],
        'timeline': ['Month 1: DSA & Git', 'Month 2: Flask & REST APIs', 'Month 3: Docker & SQL Optimization', 'Month 4: AWS & Deployment', 'Month 5: Capstone Projects', 'Month 6: Interview Preparation'],
        'certifications': ['AWS Cloud Practitioner', 'Google Data Analytics', 'Oracle Java', 'Coursera ML'],
        'projects': ['Build a REST API backend', 'Deploy a Flask app on AWS', 'Create a full-stack portfolio project'],
        'resources': ['FreeCodeCamp', 'Roadmap.sh', 'LeetCode', 'GeeksforGeeks', 'HackerRank', 'Coursera'],
        'current_readiness': 68,
        'target_readiness': 95,
        'estimated_time': '5 Months',
        'salary_current': '₹4-6 LPA',
        'salary_after_skills': '₹7-10 LPA',
        'salary_after_two_years': '₹10-15 LPA',
        'company_readiness': {'Google': 55, 'Microsoft': 60, 'Amazon': 70, 'Infosys': 92, 'TCS': 95, 'Accenture': 90},
        'weekly_plan': {'Monday': 'DSA Practice', 'Tuesday': 'SQL & Backend', 'Wednesday': 'Projects', 'Thursday': 'Git & Deployment', 'Friday': 'Docker', 'Saturday': 'Mock Interview', 'Sunday': 'Revision'},
        'ai_suggestions': 'You already have a strong programming foundation. Focus on Docker, Cloud Computing, and Data Structures to significantly improve your placement readiness. Building two production-level projects will strengthen your resume.',
        'motivation': 'Success is not about learning everything at once. It is about improving a little every single day.'
    }

    if client is not None:
        prompt = f"""
You are Bodhini AI Skill Gap Expert.
Analyze the student's current skills, compare them with industry requirements for the desired career, identify strengths and weaknesses, calculate readiness percentage, recommend missing skills, suggest certifications, projects, resources, study plans, and motivate the student.
Always answer conversationally like ChatGPT.
Avoid robotic bullet lists.
Be supportive, practical, and encouraging.

Career Goal: {form_data.get('career_goal', 'Software Engineer')}
Education: {form_data.get('education', 'B.Tech')}
Current Year: {form_data.get('current_year', '3rd Year')}
Current Skills: {form_data.get('current_skills', '')}
Skill Level: {form_data.get('skill_level', 'Beginner')}
Dream Company: {form_data.get('dream_company', 'Any company')}
Weekly Study Hours: {form_data.get('study_hours', '10 Hours')}

Return valid JSON with keys: career_goal, skill_match, readiness_status, strengths, missing_skills, priority_learning, skill_gap_table, timeline, certifications, projects, resources, current_readiness, target_readiness, estimated_time, salary_current, salary_after_skills, salary_after_two_years, company_readiness, weekly_plan, ai_suggestions, motivation.
"""
        try:
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[
                    {'role': 'system', 'content': 'You are Bodhini AI Skill Gap Expert. Analyze the student profile and return practical career guidance in JSON.'},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )
            payload = _clean_json_payload(response.choices[0].message.content)
            if payload:
                for key, value in default_report.items():
                    if key not in payload:
                        payload[key] = value
                return payload
        except Exception:
            pass

    return default_report

# =========================
# Database
# =========================

db.init_app(app)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)

with app.app_context():
    db.create_all()
    run_migrations(app)


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/error.html', code=403, title='Access Denied',
                           message='You do not have permission to access this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/error.html', code=404, title='Page Not Found',
                           message='The page you are looking for does not exist.'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('errors/error.html', code=500, title='Server Error',
                           message='Something went wrong. Please try again later.'), 500

# =========================
# Landing Page
# =========================

@app.route("/")
def landing():
    return render_template("landing.html")

# =========================
# Dashboard
# =========================

def _on_module_complete(user_id, event, description, notification_title=None, badge=None):
    """Award XP, log activity, and optionally notify after module use."""
    try:
        award_xp(user_id, event, badge)
        log_activity(user_id, event, description)
        if notification_title:
            create_notification(user_id, notification_title, description, 'success')
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    placement_predictions = PlacementPrediction.query.filter_by(
        user_id=user_id
    ).order_by(PlacementPrediction.created_at.desc()).limit(10).all()

    interviews = InterviewHistory.query.filter_by(
        user_id=user_id
    ).order_by(InterviewHistory.created_at.desc()).all()

    resume_reviews = ResumeAnalysis.query.filter_by(
        user_id=user_id
    ).order_by(ResumeAnalysis.created_at.desc()).limit(5).all()

    career_scores = compute_career_scores(user_id, (
        User, ResumeAnalysis, PlacementPrediction,
        InterviewHistory, SkillGapAnalysis, UserCertificate,
    ))
    chart_data = progress_chart_data(user_id, (
        ResumeAnalysis, PlacementPrediction, InterviewHistory, SkillGapAnalysis,
    ))
    recommendations = get_recommendations(user_id)
    activities = get_activity_timeline(user_id, limit=10)
    gamification = get_or_create_gamification(user_id)
    badges = get_badges_display(gamification)

    announcements = Announcement.query.filter_by(is_active=True).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        username=session["username"],
        placement_predictions=placement_predictions,
        career_scores=career_scores,
        chart_data=chart_data,
        recommendations=recommendations,
        activities=activities,
        gamification=gamification,
        badges=badges,
        resume_reviews=resume_reviews,
        announcements=announcements,
    )

# =========================
# Register
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            return render_template(
                "register.html",
                error="Please fill in all fields.",
                username=username,
                email=email
            )

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template(
                "register.html",
                error="An account with this email already exists. Please log in.",
                username=username,
                email=email
            )

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password=hashed_password,
            is_admin=False,
            is_active=True,
            created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        )

        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template(
                "register.html",
                error="An account with this email already exists. Please log in.",
                username=username,
                email=email
            )

        return render_template(
            "login.html",
            success="Account created successfully. Please log in.",
            email=email
        )

    return render_template("register.html")

# =========================
# Login
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        login_id = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter(
            (User.email.ilike(login_id)) |
            (User.username.ilike(login_id))
        ).first()

        password_matches = False

        if user:
            try:
                password_matches = check_password_hash(user.password, password)
            except ValueError:
                password_matches = False

            if not password_matches and user.password == password:
                user.password = generate_password_hash(password)
                db.session.commit()
                password_matches = True

        if user and password_matches:

            if not user.is_active:
                return render_template(
                    "login.html",
                    error="Your account has been disabled. Contact support.",
                    email=login_id
                )

            session["user_id"] = user.id
            session["username"] = user.username
            user.last_login = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            db.session.commit()

            if user.is_admin:
                session["is_admin"] = True
                return redirect(url_for("admin.dashboard"))

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=login_id
        )

    return render_template("login.html")

# =========================
# Reset Password
# =========================

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not email or not new_password or not confirm_password:
            return render_template(
                "reset_password.html",
                error="Please fill in all fields.",
                email=email
            )

        if new_password != confirm_password:
            return render_template(
                "reset_password.html",
                error="Passwords do not match.",
                email=email
            )

        user = User.query.filter(User.email.ilike(email)).first()

        if not user:
            return render_template(
                "reset_password.html",
                error="No account exists with this email.",
                email=email
            )

        user.password = generate_password_hash(new_password)
        db.session.commit()

        return render_template(
            "login.html",
            success="Password reset successfully. Please log in.",
            email=user.email
        )

    return render_template("reset_password.html")

# =========================
# Logout
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# =========================
# Users (Testing)
# =========================


# =========================
# AI Chat
# =========================

# =========================
# AI Chat
# =========================

@app.route("/chat", methods=["GET", "POST"])
def chat():

    if "user_id" not in session:
        return redirect("/login")

    response_text = ""

    if request.method == "POST":

        prompt = request.form["prompt"]

        if client is None:

            response_text = (
                "Bodhini AI is currently unavailable. "
                "Please check your API configuration."
            )

        else:

            try:

                chat_completion = client.chat.completions.create(

                    messages=[

                        {
                            "role": "system",
                            "content": """
You are Bodhini AI, a modern AI Career Coach, Placement Mentor, and Learning Assistant.

Your mission is to help students grow academically, professionally, and personally.

PERSONALITY:

- Friendly and supportive
- Professional and intelligent
- Motivational but realistic
- Career-focused
- Easy to understand
- Modern and conversational

IMPORTANT RULES:

1. Respond naturally like ChatGPT.
2. Never sound robotic.
3. Never sound like a report generator.
4. Avoid excessive markdown tables.
5. Use clean formatting.
6. Explain concepts in simple language.
7. Give practical advice.
8. Personalize responses whenever possible.
9. Encourage students and build confidence.
10. Keep answers structured and engaging.

YOUR EXPERTISE:

- Career Guidance
- Placement Preparation
- Resume Reviews
- Interview Preparation
- Learning Roadmaps
- Skill Development
- Project Suggestions
- Industry Trends
- Productivity & Growth

RESPONSE FRAMEWORK:

Always try to follow:

Question
↓
Conversation
↓
Guidance
↓
Action Plan

For example:

If user asks:
"What is SQL?"

Do not give a textbook definition only.

Explain simply, then tell why it matters for placements and careers.

If user asks:
"I'm confused about my career."

Start by understanding their situation.
Then guide them.
Then provide next steps.

ACTION PLAN FORMAT:

Whenever suitable, end responses with:

🎯 Next Steps

1. ...
2. ...
3. ...

Keep responses human, professional, and mentor-like.

You are not just an AI chatbot.

You are a trusted career coach helping students succeed.
"""
                        },

                        {
                            "role": "user",
                            "content": prompt
                        }

                    ],

                    model="llama-3.3-70b-versatile"
                )

                response_text = (
                    chat_completion
                    .choices[0]
                    .message
                    .content
                    .strip()
                )

                log = AIChatLog(
                    user_id=session["user_id"],
                    prompt=prompt,
                    response=response_text,
                    module_used="AI Career Chat",
                    created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                )
                db.session.add(log)
                db.session.commit()
                _on_module_complete(session["user_id"], 'chat', 'AI Chat session completed',
                                    'Chat Session', None)

            except Exception as e:

                response_text = (
                    f"Bodhini AI Error: {str(e)}"
                )

    return render_template(
        "chat.html",
        response=response_text,
        prompt=request.form.get("prompt", "")
    )


def _is_allowed_resume(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in {"pdf", "docx"}
    )


def _load_resume_report(review):
    try:
        return json.loads(review.feedback)
    except Exception:
        return {
            "resume_name": review.resume_name,
            "target_role": "Software Engineer",
            "candidate_name": "Not detected",
            "detected_role": "Software Engineer",
            "experience_level": "Entry Level",
            "education": "Not detected",
            "skills_count": 0,
            "projects_count": 0,
            "certifications_count": 0,
            "resume_pages": 1,
            "reading_time": "1 min",
            "ats_score": review.ats_score,
            "resume_score": review.resume_score,
            "potential_score": min(98, review.ats_score + 15),
            "keyword_match": review.ats_score,
            "matched_keywords": [],
            "missing_keywords": [],
            "compatibility": [],
            "sections": [],
            "formatting": [],
            "strengths": ["Saved legacy resume review"],
            "improvements": ["Run a new ATS scan for the premium report format"],
            "missing_sections": [],
            "recruiter_view": {"pros": [], "cons": [], "overall": "Run a new scan to generate recruiter insights."},
            "company_readiness": [],
            "recommendations": [],
            "quality_meter": [],
            "career_suggestions": {"roles": [], "projects": [], "skills": [], "courses": [], "certifications": []},
            "rewrite_suggestions": [],
            "heatmap": [],
            "summary": review.feedback or "",
            "final_advice": "Run a new scan to generate the full ATS report."
        }


@app.route("/resume", methods=["GET", "POST"])
@app.route("/ats-resume-checker", methods=["GET", "POST"])
def resume():

    if "user_id" not in session:
        return redirect("/login")

    target_roles = [
        "Software Engineer",
        "Python Developer",
        "Data Analyst",
        "ML Engineer",
        "Web Developer",
        "Backend Developer"
    ]
    recent_reviews = ResumeAnalysis.query.filter_by(
        user_id=session["user_id"]
    ).order_by(ResumeAnalysis.created_at.desc()).limit(6).all()

    if request.method == "POST":

        if "resume" not in request.files:
            return render_template(
                "resume_checker.html",
                error="Please choose a PDF or DOCX resume before analyzing.",
                target_roles=target_roles,
                recent_reviews=recent_reviews
            )

        file = request.files["resume"]
        target_role = request.form.get("target_role", "Software Engineer").strip() or "Software Engineer"

        if file.filename == "":
            return render_template(
                "resume_checker.html",
                error="Please choose a resume file before analyzing.",
                target_roles=target_roles,
                recent_reviews=recent_reviews,
                selected_role=target_role
            )

        if not _is_allowed_resume(file.filename):
            return render_template(
                "resume_checker.html",
                error="Unsupported file type. Upload a PDF or DOCX resume.",
                target_roles=target_roles,
                recent_reviews=recent_reviews,
                selected_role=target_role
            )

        if request.content_length and request.content_length > app.config["MAX_CONTENT_LENGTH"]:
            return render_template(
                "resume_checker.html",
                error="File is too large. Maximum upload size is 5 MB.",
                target_roles=target_roles,
                recent_reviews=recent_reviews,
                selected_role=target_role
            )

        selected_name = secure_filename(file.filename)
        filename = f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{selected_name}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        try:
            resume_text = extract_text_from_file(save_path)
        except Exception as e:
            return render_template(
                "resume_checker.html",
                error=f"The uploaded file could not be processed: {str(e)}",
                target_roles=target_roles,
                recent_reviews=recent_reviews,
                selected_role=target_role
            )

        raw_response = analyze_resume(resume_text, client=client)
        analysis_data = parse_resume_analysis(raw_response)
        report = build_premium_ats_report(
            resume_text=resume_text,
            base_analysis=analysis_data,
            resume_name=selected_name,
            target_role=target_role
        )

        static_resume_path = os.path.join('uploads', 'resumes', filename)
        resume_static_dir = os.path.join(app.root_path, 'static', 'uploads', 'resumes')
        os.makedirs(resume_static_dir, exist_ok=True)
        shutil.copy2(save_path, os.path.join(resume_static_dir, filename))

        review = ResumeAnalysis(
            user_id=session["user_id"],
            resume_score=report["resume_score"],
            ats_score=report["ats_score"],
            feedback=json.dumps(report),
            resume_name=selected_name,
            file_path=static_resume_path,
            keyword_match=report.get("keyword_match", report["ats_score"]),
            formatting_score=report.get("formatting_score", 0),
            grammar_score=report.get("grammar_score", 0),
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )

        db.session.add(review)
        db.session.commit()
        _on_module_complete(session["user_id"], 'resume_upload', f'Resume analyzed: {selected_name}',
                            'Resume Improved', 'resume_master')
        if review.ats_score and review.ats_score >= 70:
            create_notification(session["user_id"], 'ATS Score Updated',
                                f'Your ATS score is {review.ats_score}%', 'success')
            db.session.commit()

        return redirect(url_for("ats_resume_result", review_id=review.id))

    return render_template(
        "resume_checker.html",
        target_roles=target_roles,
        recent_reviews=recent_reviews,
        selected_role="Software Engineer"
    )


@app.route("/ats-resume-result/<int:review_id>")
def ats_resume_result(review_id):

    if "user_id" not in session:
        return redirect("/login")

    review = ResumeAnalysis.query.filter_by(
        id=review_id,
        user_id=session["user_id"]
    ).first_or_404()
    report = _load_resume_report(review)

    return render_template(
        "resume_result.html",
        review=review,
        report=report,
        share_url=url_for("ats_resume_result", review_id=review.id, _external=True)
    )


@app.route("/ats-resume-report/<int:review_id>/download")
def ats_resume_report_download(review_id):

    if "user_id" not in session:
        return redirect("/login")

    review = ResumeAnalysis.query.filter_by(
        id=review_id,
        user_id=session["user_id"]
    ).first_or_404()
    report = _load_resume_report(review)

    return render_template(
        "resume_result.html",
        review=review,
        report=report,
        printable=True,
        share_url=url_for("ats_resume_result", review_id=review.id, _external=True)
    )


@app.route("/placement-predictor", methods=["GET", "POST"])
def placement_predictor():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        required_fields = [
            "student_name",
            "college_name",
            "branch",
            "current_year",
            "city",
            "cgpa",
            "tenth_percentage",
            "twelfth_percentage",
            "backlogs"
        ]

        if any(not request.form.get(field, "").strip() for field in required_fields):
            return render_template(
                "placement_predictor.html",
                error="Please fill in all required profile details before predicting."
            )

        form_data = request.form.to_dict()

        if client is None:
            result = analyze_profile(form_data, client=None)
        else:
            result = analyze_profile(form_data, client=client)

        prediction = PlacementPrediction(
            user_id=session["user_id"],
            student_name=form_data.get("student_name", ""),
            college=form_data.get("college_name", ""),
            branch=form_data.get("branch", ""),
            cgpa=form_data.get("cgpa", ""),
            prediction_score=result.get("placement_probability", 0),
            expected_package=result.get("expected_salary", ""),
            placement_chance=result.get("readiness_level", ""),
            strengths=json.dumps(result.get("strengths", [])),
            weaknesses=json.dumps(result.get("weak_areas", [])),
            career_advice=result.get("career_advice", ""),
            timeline=str(result.get("timeline", {})),
            daily_tasks=str(result.get("daily_tasks", [])),
            created_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )

        db.session.add(prediction)
        db.session.commit()
        _on_module_complete(session["user_id"], 'placement_predict', 'Placement prediction generated',
                            'Placement Readiness Updated')

        session["latest_prediction_data"] = result
        session["latest_prediction_id"] = prediction.id

        return redirect(url_for("prediction_report", prediction_id=prediction.id))

    return render_template("placement_predictor.html", error=None)


@app.route("/prediction-report/<int:prediction_id>")
def prediction_report(prediction_id):

    if "user_id" not in session:
        return redirect("/login")

    prediction = PlacementPrediction.query.filter_by(
        id=prediction_id,
        user_id=session["user_id"]
    ).first()

    if not prediction:
        return redirect(url_for("placement_predictor"))

    result = session.get("latest_prediction_data") or {
        "placement_probability": prediction.prediction_score or 0,
        "expected_salary": prediction.expected_package or "₹5-8 LPA",
        "readiness_level": "Intermediate",
        "strengths": ["Python", "SQL", "Projects"],
        "weak_areas": ["Communication", "Cloud", "DSA"],
        "missing_skills": ["AWS", "Docker", "System Design"],
        "recommended_projects": ["AI Career Coach", "Portfolio Website"],
        "certifications": ["AWS Cloud Practitioner", "Oracle SQL"],
        "target_companies": ["Google", "Microsoft", "Amazon"],
        "resume_suggestions": ["Add quantified achievements", "Improve summary section", "Include GitHub and LinkedIn"],
        "career_advice": prediction.career_advice or "Keep building practical projects and improving your technical fundamentals.",
        "timeline": {"current_readiness": max(60, prediction.prediction_score - 10), "thirty_day_goal": min(90, max(70, prediction.prediction_score + 5)), "sixty_day_goal": min(95, max(80, prediction.prediction_score + 10)), "ninety_day_goal": 95},
        "daily_tasks": ["Solve 2 DSA problems", "Practice SQL for 30 minutes", "Improve one resume bullet"],
        "weekly_roadmap": ["Week 1: DSA", "Week 2: SQL", "Week 3: Git + GitHub", "Week 4: Cloud", "Week 5: Projects", "Week 6: Mock Interviews"],
        "radar_scores": {"coding": 78, "communication": 72, "projects": 76, "academics": 82, "leadership": 74, "problem_solving": 70, "technical_skills": 80},
        "interview_questions": ["Explain OOP", "What is indexing?"],
        "hr_questions": ["Tell me about yourself", "Why should we hire you?"],
        "aptitude_topics": ["Percentages", "Ratios"],
        "coding_topics": ["Arrays", "Linked List"]
    }

    previous_predictions = PlacementPrediction.query.filter_by(
        user_id=session["user_id"]
    ).order_by(PlacementPrediction.created_at.desc()).limit(5).all()

    return render_template(
        "prediction_result.html",
        prediction=prediction,
        result=result,
        previous_predictions=previous_predictions
    )


@app.route('/career-roadmap', methods=['GET', 'POST'])
def career_roadmap():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        form_data = request.form.to_dict()
        roadmap_result = generate_roadmap(form_data, client=client)

        roadmap_entry = CareerRoadmap(
            user_id=session['user_id'],
            career_goal=form_data.get('career_goal', ''),
            education=form_data.get('education', ''),
            current_year=form_data.get('current_year', ''),
            skill_level=form_data.get('skill_level', ''),
            study_time=form_data.get('study_time', ''),
            learning_style=form_data.get('learning_style', ''),
            roadmap_data=json.dumps(roadmap_result),
            created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(roadmap_entry)
        db.session.commit()
        _on_module_complete(session['user_id'], 'roadmap', f'Career roadmap created: {form_data.get("career_goal", "")}',
                            'Roadmap Updated')

        session['latest_roadmap_data'] = roadmap_result
        session['latest_roadmap_id'] = roadmap_entry.id

        return redirect(url_for('career_roadmap_result', roadmap_id=roadmap_entry.id))

    return render_template('career_roadmap.html', error=None)


@app.route('/career-roadmap/result/<int:roadmap_id>')
def career_roadmap_result(roadmap_id):
    if 'user_id' not in session:
        return redirect('/login')

    roadmap_entry = CareerRoadmap.query.filter_by(id=roadmap_id, user_id=session['user_id']).first()
    if not roadmap_entry:
        return redirect(url_for('career_roadmap'))

    roadmap_data = session.get('latest_roadmap_data') or json.loads(roadmap_entry.roadmap_data)
    previous_roadmaps = CareerRoadmap.query.filter_by(user_id=session['user_id']).order_by(CareerRoadmap.created_at.desc()).limit(5).all()

    return render_template('career_roadmap_result.html', roadmap=roadmap_data, previous_roadmaps=previous_roadmaps)


@app.route('/skill-gap', methods=['GET', 'POST'])
def skill_gap():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        form_data = request.form.to_dict()
        report = _generate_skill_gap_report(form_data)

        analysis = SkillGapAnalysis(
            user_id=session['user_id'],
            career_goal=form_data.get('career_goal', ''),
            current_skills=form_data.get('current_skills', ''),
            skill_match=report.get('skill_match', 0),
            missing_skills=json.dumps(report.get('missing_skills', [])),
            roadmap=json.dumps(report),
            created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        )
        db.session.add(analysis)
        db.session.commit()
        _on_module_complete(session['user_id'], 'skill_gap', 'Skill gap analysis completed',
                            'Skills Analyzed', 'skill_builder')

        session['latest_skill_gap_report'] = report
        session['latest_skill_gap_id'] = analysis.id
        return redirect(url_for('skill_gap_result'))

    return render_template('skill_gap.html')


@app.route('/skill-gap/result')
def skill_gap_result():
    if 'user_id' not in session:
        return redirect('/login')

    report = session.get('latest_skill_gap_report')
    if not report:
        analyses = SkillGapAnalysis.query.filter_by(user_id=session['user_id']).order_by(SkillGapAnalysis.created_at.desc()).all()
        if analyses:
            report = json.loads(analyses[0].roadmap)
        else:
            return redirect(url_for('skill_gap'))

    return render_template('skill_gap_result.html', report=report)


@app.route('/skill-gap/history')
def skill_gap_history():
    if 'user_id' not in session:
        return redirect('/login')

    history = SkillGapAnalysis.query.filter_by(user_id=session['user_id']).order_by(SkillGapAnalysis.created_at.desc()).all()
    return render_template('skill_gap_history.html', history=history)


@app.route('/delete-analysis/<int:analysis_id>')
def delete_analysis(analysis_id):
    if 'user_id' not in session:
        return redirect('/login')

    analysis = SkillGapAnalysis.query.filter_by(id=analysis_id, user_id=session['user_id']).first()
    if analysis:
        db.session.delete(analysis)
        db.session.commit()

    return redirect(url_for('skill_gap_history'))


@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if 'user_id' not in session:
        return redirect('/login')

    interview_type = session.get('interview_type', 'Mock Interview')
    difficulty = session.get('interview_difficulty', 'Medium')
    target_company = session.get('interview_company', '')
    conversation = session.get('interview_conversation', [])
    question_count = session.get('interview_question_count', 0)
    interview_completed = session.get('interview_completed', False)
    interview_summary = session.get('interview_summary')
    history = InterviewHistory.query.filter_by(user_id=session['user_id']).order_by(InterviewHistory.created_at.desc()).limit(5).all()

    common_questions = [
        'Tell me about yourself',
        'Difference between SQL and NoSQL',
        'Explain OOP',
        'Python vs Java',
        'Explain DBMS',
        'Explain Machine Learning',
        'Strengths',
        'Weaknesses',
        'Leadership',
        'Conflict Resolution'
    ]

    if request.method == 'POST':
        action = request.form.get('action', 'start')

        if action == 'start':
            interview_type = request.form.get('interview_type', 'Mock Interview')
            difficulty = request.form.get('difficulty', 'Medium')
            target_company = request.form.get('target_company', '').strip()
            conversation = []
            question_count = 0
            interview_completed = False
            interview_summary = None

            first_question = _generate_interview_question(interview_type, difficulty, target_company, 'Start of interview')
            conversation.append({
                'role': 'ai',
                'kind': 'question',
                'content': first_question.get('question', 'Tell me about yourself.'),
                'focus_area': first_question.get('focus_area', 'Interview readiness'),
                'expected_answer_hint': first_question.get('expected_answer_hint', 'Be concise and structured')
            })

        elif action == 'answer':
            user_answer = request.form.get('answer', '').strip()
            if user_answer:
                conversation.append({'role': 'user', 'kind': 'answer', 'content': user_answer})
                question_count += 1

                feedback = _generate_interview_feedback(
                    interview_type,
                    difficulty,
                    target_company,
                    _serialize_conversation(conversation),
                    user_answer
                )

                conversation.append({
                    'role': 'ai',
                    'kind': 'feedback',
                    'content': f"Overall score: {feedback.get('overall_score', 0)}/10. Focus on clarity, confidence, and structure.",
                    'feedback': feedback
                })

                if question_count >= 5:
                    summary = _generate_interview_summary(
                        interview_type,
                        difficulty,
                        target_company,
                        _serialize_conversation(conversation)
                    )
                    interview_completed = True
                    interview_summary = summary
                    conversation.append({
                        'role': 'ai',
                        'kind': 'summary',
                        'content': 'Interview completed. Here is your final performance summary.',
                        'feedback': summary
                    })

                    history_entry = InterviewHistory(
                        user_id=session['user_id'],
                        interview_type=interview_type,
                        company=target_company or 'Custom',
                        difficulty=difficulty,
                        overall_score=summary.get('overall_score', feedback.get('overall_score', 0)),
                        total_questions=question_count,
                        average_feedback=str(summary.get('overall_score', feedback.get('overall_score', 0))),
                        questions_data=json.dumps(conversation),
                        feedback_data=json.dumps(summary),
                        communication_rating=summary.get('communication_score', feedback.get('communication_score', 0)),
                        technical_rating=summary.get('technical_score', feedback.get('technical_score', 0)),
                        confidence_rating=summary.get('confidence_score', feedback.get('confidence_score', 0)),
                        created_at=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    db.session.add(history_entry)
                    db.session.commit()
                    _on_module_complete(session['user_id'], 'interview_complete', 'Mock interview completed',
                                        'Interview Completed', 'interview_expert')
                else:
                    next_question = _generate_interview_question(
                        interview_type,
                        difficulty,
                        target_company,
                        _serialize_conversation(conversation)
                    )
                    conversation.append({
                        'role': 'ai',
                        'kind': 'question',
                        'content': next_question.get('question', 'Tell me about one difficult project you handled.'),
                        'focus_area': next_question.get('focus_area', 'Next challenge'),
                        'expected_answer_hint': next_question.get('expected_answer_hint', 'Use a structured answer')
                    })

        session['interview_type'] = interview_type
        session['interview_difficulty'] = difficulty
        session['interview_company'] = target_company
        session['interview_conversation'] = conversation
        session['interview_question_count'] = question_count
        session['interview_completed'] = interview_completed
        session['interview_summary'] = interview_summary

    return render_template(
        'interview.html',
        interview_type=interview_type,
        difficulty=difficulty,
        target_company=target_company,
        conversation=conversation,
        question_count=question_count,
        interview_completed=interview_completed,
        interview_summary=interview_summary,
        history=history,
        common_questions=common_questions
    )

# =========================
# Run App
# =========================

if __name__ == "__main__":
    app.run(debug=True)
