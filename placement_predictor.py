import os
import json
import re
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
You are Bodhini AI, an expert HR Recruiter, Placement Mentor, Career Coach, and Engineering Interview Specialist.
Analyze the student's profile realistically and provide a placement readiness assessment.
Use the supplied skill and communication ratings as the main evidence for readiness.
If GitHub or LinkedIn profile URLs are provided, treat them as evidence of projects, contributions, internships, or professional work and mention them in your assessment.
Return a JSON object with these fields:
- placement_probability: integer between 0 and 100
- expected_salary: string
- readiness_level: string
- strengths: list of strings
- weak_areas: list of strings
- missing_skills: list of strings
- recommended_projects: list of strings
- certifications: list of strings
- target_companies: list of strings
- interview_questions: list of strings
- hr_questions: list of strings
- aptitude_topics: list of strings
- coding_topics: list of strings
- career_advice: string
- timeline: object with current_readiness, thirty_day_goal, sixty_day_goal, ninety_day_goal
- daily_tasks: list of strings
- weekly_roadmap: list of strings
- radar_scores: object with coding, communication, projects, academics, leadership, problem_solving, technical_skills
Be practical, encouraging, and conversational.
"""


def build_prompt(form_data):
    return f"""
Student Profile:
Name: {form_data.get('student_name', '')}
College: {form_data.get('college_name', '')}
Branch: {form_data.get('branch', '')}
Current Year: {form_data.get('current_year', '')}
City: {form_data.get('city', '')}
CGPA: {form_data.get('cgpa', '')}
10th Percentage: {form_data.get('tenth_percentage', '')}
12th Percentage: {form_data.get('twelfth_percentage', '')}
Backlogs: {form_data.get('backlogs', '')}
Skills: Python={form_data.get('python', '')}, Java={form_data.get('java', '')}, C++={form_data.get('cpp', '')}, SQL={form_data.get('sql', '')}, JavaScript={form_data.get('javascript', '')}, HTML={form_data.get('html', '')}, CSS={form_data.get('css', '')}, React={form_data.get('react', '')}, Node.js={form_data.get('nodejs', '')}, Flask={form_data.get('flask', '')}, Django={form_data.get('django', '')}, Machine Learning={form_data.get('ml', '')}, Deep Learning={form_data.get('dl', '')}, Data Structures={form_data.get('dsa', '')}, Algorithms={form_data.get('algorithms', '')}, OS={form_data.get('os', '')}, DBMS={form_data.get('dbms', '')}, Computer Networks={form_data.get('cn', '')}, Cloud Computing={form_data.get('cloud', '')}, AWS={form_data.get('aws', '')}, Docker={form_data.get('docker', '')}, Git={form_data.get('git', '')}, GitHub={form_data.get('github', '')}
Communication: {form_data.get('communication', '')}
Leadership: {form_data.get('leadership', '')}
Teamwork: {form_data.get('teamwork', '')}
Presentation: {form_data.get('presentation', '')}
Confidence: {form_data.get('confidence', '')}
Projects: {form_data.get('projects_completed', '')}
Internships: {form_data.get('internships', '')}
Hackathons: {form_data.get('hackathons', '')}
Certifications: {form_data.get('certifications', '')}
Coding Competitions: {form_data.get('coding_competitions', '')}
Open Source: {form_data.get('open_source', '')}
GitHub Profile: {form_data.get('github_profile', '')}
LinkedIn Profile: {form_data.get('linkedin_profile', '')}
Career Goal: {form_data.get('career_goal', '')}
"""


def _parse_rating(value):
    try:
        rating = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if rating < 0:
        return 0
    if rating > 10:
        return 10
    return rating


def _build_fallback_result(form_data):
    skill_keys = ['python', 'java', 'cpp', 'sql', 'javascript', 'html', 'css', 'react', 'nodejs', 'flask', 'django', 'ml', 'dl', 'dsa', 'algorithms', 'os', 'dbms', 'cn', 'cloud', 'aws', 'docker', 'git', 'github']
    communication_keys = ['communication', 'leadership', 'teamwork', 'presentation', 'confidence', 'projects_completed', 'internships', 'hackathons', 'certifications', 'coding_competitions', 'open_source', 'github_profile', 'linkedin_profile']

    skill_ratings = [rating for key in skill_keys if (rating := _parse_rating(form_data.get(key, ''))) is not None and rating > 0]
    communication_ratings = [rating for key in communication_keys if (rating := _parse_rating(form_data.get(key, ''))) is not None and rating > 0]

    skill_avg = sum(skill_ratings) / len(skill_ratings) if skill_ratings else 5.0
    communication_avg = sum(communication_ratings) / len(communication_ratings) if communication_ratings else 5.0

    cgpa = _parse_rating(form_data.get('cgpa', '')) or 0
    tenth = _parse_rating(form_data.get('tenth_percentage', '')) or 0
    twelfth = _parse_rating(form_data.get('twelfth_percentage', '')) or 0

    academic_score = 0
    if cgpa > 0:
        academic_score += (cgpa / 10.0) * 40
    if tenth > 0:
        academic_score += (tenth / 100.0) * 30
    if twelfth > 0:
        academic_score += (twelfth / 100.0) * 30
    if academic_score == 0:
        academic_score = 65

    score = int(round((academic_score * 0.4) + (skill_avg * 10 * 0.35) + (communication_avg * 10 * 0.25)))
    score = max(35, min(95, score))

    if score >= 85:
        readiness = 'Excellent'
        salary = '₹10-16 LPA'
    elif score >= 70:
        readiness = 'Strong'
        salary = '₹7-10 LPA'
    else:
        readiness = 'Developing'
        salary = '₹5-7 LPA'

    strengths = []
    weak_areas = []
    if skill_avg >= 7:
        strengths.append('Strong technical foundation')
    else:
        weak_areas.append('Technical depth')
    if communication_avg >= 7:
        strengths.append('Good communication and presentation')
    else:
        weak_areas.append('Communication and confidence')
    if cgpa >= 8:
        strengths.append('Solid academic profile')
    else:
        weak_areas.append('Academic consistency')

    if not strengths:
        strengths = ['Technical consistency', 'Project focus']
    if not weak_areas:
        weak_areas = ['Cloud and system design', 'Interview readiness']

    return {
        'placement_probability': score,
        'expected_salary': salary,
        'readiness_level': readiness,
        'strengths': strengths,
        'weak_areas': weak_areas,
        'missing_skills': ['Docker', 'AWS', 'System Design', 'Data Structures'],
        'recommended_projects': ['AI Career Coach', 'Portfolio Website', 'REST API Service'],
        'certifications': ['AWS Cloud Practitioner', 'Oracle SQL'],
        'target_companies': ['Google', 'Microsoft', 'Infosys', 'TCS'],
        'resume_suggestions': ['Add quantified achievements', 'Improve your summary section', 'Highlight GitHub and projects'],
        'interview_questions': ['Explain OOP concepts', 'What is SQL indexing?'],
        'hr_questions': ['Tell me about yourself', 'Why do you want this role?'],
        'aptitude_topics': ['Percentages', 'Ratios'],
        'coding_topics': ['Arrays', 'Linked List'],
        'career_advice': 'Your rating-based profile suggests a solid foundation. Keep strengthening core DSA, cloud basics, and communication to improve your placement readiness.',
        'timeline': {
            'current_readiness': max(55, score - 8),
            'thirty_day_goal': min(90, max(65, score + 4)),
            'sixty_day_goal': min(95, max(75, score + 8)),
            'ninety_day_goal': 95,
        },
        'daily_tasks': ['Solve 2 DSA problems', 'Practice SQL for 30 minutes', 'Improve one project demo'],
        'weekly_roadmap': ['Week 1: Improve DSA', 'Week 2: SQL', 'Week 3: Git + GitHub', 'Week 4: Cloud', 'Week 5: Projects', 'Week 6: Mock Interviews'],
        'radar_scores': {
            'coding': int(round(skill_avg * 10)),
            'communication': int(round(communication_avg * 10)),
            'projects': int(round(min(10, (skill_avg + communication_avg) / 2) * 10)),
            'academics': int(round(min(100, academic_score))),
            'leadership': int(round(communication_avg * 10)),
            'problem_solving': int(round(min(100, score - 5))),
            'technical_skills': int(round(skill_avg * 10)),
        },
    }


def analyze_profile(form_data, client=None, model='llama-3.3-70b-versatile'):
    if client is None:
        return _build_fallback_result(form_data)

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
        return analyze_profile(form_data)
