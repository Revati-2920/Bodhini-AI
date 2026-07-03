import json
import os

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are Bodhini AI, an elite career coach and learning strategist.
Create a highly personalized career roadmap for a student.
Write naturally, like ChatGPT, not like a robot or a template.
Be encouraging, specific, practical, and realistic.
Return valid JSON with the following structure:
{
  "career_goal": "",
  "current_level": "",
  "target_role": "",
  "expected_preparation_time": "",
  "difficulty": "",
  "skill_gap": {
    "already_strong": [""],
    "needs_improvement": [""],
    "missing_skills": [""],
    "soft_skills": [""]
  },
  "learning_roadmap": [
    {"month": "Month 1", "focus": "", "outcomes": [""]}
  ],
  "resources": [
    {"name": "", "type": "", "link": ""}
  ],
  "projects": [
    {"title": "", "purpose": "", "skills_learned": "", "difficulty": ""}
  ],
  "certifications": [""],
  "weekly_plan": {
    "Monday": "",
    "Tuesday": "",
    "Wednesday": "",
    "Thursday": "",
    "Friday": "",
    "Saturday": "",
    "Sunday": ""
  },
  "interview_preparation": {
    "topics": [""],
    "behavioral": [""],
    "hr": [""],
    "system_design": [""],
    "communication": [""]
  },
  "companies_to_target": [""],
  "expected_salary": {
    "fresher": "",
    "one_year": "",
    "three_years": "",
    "five_years": ""
  },
  "motivation": ""
}
"""


def build_prompt(form_data):
    return f"""
Student Details:
Career Goal: {form_data.get('career_goal', '')}
Current Education: {form_data.get('education', '')}
Current Year: {form_data.get('current_year', '')}
Current Skills: {form_data.get('current_skills', '')}
Skill Level: {form_data.get('skill_level', '')}
Study Time: {form_data.get('study_time', '')}
Learning Style: {form_data.get('learning_style', '')}

Create a roadmap that is tailored to the student's background and the target role.
"""


def _fallback_roadmap(form_data):
    career_goal = form_data.get('career_goal', 'Software Engineer')
    skill_level = form_data.get('skill_level', 'Intermediate')
    study_time = form_data.get('study_time', '3 hours/day')
    current_skills = [item.strip() for item in form_data.get('current_skills', '').split(',') if item.strip()]

    if not current_skills:
        current_skills = ['Python', 'SQL']

    strong = current_skills[:min(3, len(current_skills))]
    missing = ['Data Structures', 'System Design', 'Cloud Basics']
    if career_goal.lower().startswith('data'):
        missing = ['SQL', 'Statistics', 'Python', 'Machine Learning']
    elif 'cloud' in career_goal.lower() or 'devops' in career_goal.lower():
        missing = ['Linux', 'Networking', 'Docker', 'AWS']
    elif 'ui' in career_goal.lower() or 'frontend' in career_goal.lower():
        missing = ['React', 'UI Design', 'Accessibility']

    return {
        "career_goal": career_goal,
        "current_level": skill_level,
        "target_role": career_goal,
        "expected_preparation_time": study_time,
        "difficulty": "Moderate",
        "skill_gap": {
            "already_strong": strong,
            "needs_improvement": ['Problem Solving', 'Git/GitHub', 'Projects'],
            "missing_skills": missing,
            "soft_skills": ['Communication', 'Resume Writing', 'Interview Confidence']
        },
        "learning_roadmap": [
            {"month": "Month 1", "focus": "Build core fundamentals", "outcomes": ["Strengthen Python basics", "Practice Git and GitHub", "Complete 1 mini project"]},
            {"month": "Month 2", "focus": "Practice problem solving", "outcomes": ["Solve 40 DSA questions", "Understand SQL and DBMS", "Write clean code"]},
            {"month": "Month 3", "focus": "Build portfolio projects", "outcomes": ["Create 2 polished projects", "Deploy one app", "Improve documentation"]},
            {"month": "Month 4", "focus": "Interview and resume prep", "outcomes": ["Mock interviews", "Refine resume", "Prepare behavioral stories"]},
            {"month": "Month 5", "focus": "Deepen domain expertise", "outcomes": ["Learn system design basics", "Practice case studies", "Improve communication"]},
            {"month": "Month 6", "focus": "Apply and optimize", "outcomes": ["Apply to target companies", "Publish your portfolio", "Keep improving"]}
        ],
        "resources": [
            {"name": "FreeCodeCamp", "type": "YouTube", "link": "https://www.freecodecamp.org/"},
            {"name": "Roadmap.sh", "type": "Documentation", "link": "https://roadmap.sh/"},
            {"name": "LeetCode", "type": "Practice", "link": "https://leetcode.com/"},
            {"name": "Coursera", "type": "Course", "link": "https://www.coursera.org/"}
        ],
        "projects": [
            {"title": "Personal Portfolio Website", "purpose": "Showcase your skills and projects", "skills_learned": "Frontend, GitHub, Deployment", "difficulty": "Beginner"},
            {"title": "Task Manager App", "purpose": "Practice CRUD, authentication, and database handling", "skills_learned": "Flask, SQL, APIs", "difficulty": "Intermediate"},
            {"title": "Capstone Project", "purpose": "Build a full product that demonstrates end-to-end thinking", "skills_learned": "Architecture, Deployment, Testing", "difficulty": "Advanced"}
        ],
        "certifications": ["Google Data Analytics", "AWS Cloud Practitioner", "Microsoft Azure Fundamentals"],
        "weekly_plan": {
            "Monday": "Core study block and revision",
            "Tuesday": "Hands-on coding practice",
            "Wednesday": "Projects and debugging",
            "Thursday": "DSA or interview prep",
            "Friday": "Resume and portfolio updates",
            "Saturday": "Long project session",
            "Sunday": "Review and reflection"
        },
        "interview_preparation": {
            "topics": ["DSA", "Core Subjects", "System Design"],
            "behavioral": ["Tell me about yourself", "Why this role?"],
            "hr": ["Strengths and weaknesses", "Career goals"],
            "system_design": ["Design a URL shortener", "Design a chat application"],
            "communication": ["Explain your projects clearly", "Practice speaking with confidence"]
        },
        "companies_to_target": ["Google", "Microsoft", "Amazon", "Infosys", "TCS", "Accenture"],
        "expected_salary": {
            "fresher": "₹4-7 LPA",
            "one_year": "₹6-9 LPA",
            "three_years": "₹10-15 LPA",
            "five_years": "₹15-25 LPA"
        },
        "motivation": "You already have a strong foundation. The key now is consistency, project-building, and focused practice. With a clear roadmap, your next step will feel much more achievable."
    }


def generate_roadmap(form_data, client=None, model='llama-3.3-70b-versatile'):
    if client is None:
        return _fallback_roadmap(form_data)

    try:
        completion = client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': build_prompt(form_data)}
            ],
            model=model
        )
        text = completion.choices[0].message.content.strip()
        return json.loads(text)
    except Exception:
        return _fallback_roadmap(form_data)
