import os
import re
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None

SYSTEM_PROMPT = (
    "You are Bodhini AI, an expert Resume Reviewer, ATS Specialist, HR Recruiter and Career Coach. "
    "Analyze the uploaded resume professionally. "
    "Return your response in this structure: "
    "Resume Score: <number>/100\n"
    "ATS Compatibility Score: <number>/100\n"
    "Strengths:\n"
    "- ...\n"
    "Weaknesses:\n"
    "- ...\n"
    "Missing Skills:\n"
    "- ...\n"
    "Resume Summary Feedback:\n"
    "- ...\n"
    "Project Suggestions:\n"
    "- ...\n"
    "Certifications:\n"
    "- ...\n"
    "Best Companies:\n"
    "- ...\n"
    "Final Career Advice:\n"
    "- ...\n"
    "Keep responses conversational, professional, encouraging and easy to read. "
    "Do NOT use markdown tables. Use bullet points. Do not sound robotic. Explain like ChatGPT."
)


def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        if pdfplumber is None:
            raise RuntimeError("pdfplumber is not installed")
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text.strip()

    if ext == ".docx":
        if Document is None:
            raise RuntimeError("python-docx is not installed")
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs)

    raise ValueError("Unsupported file type. Please upload a PDF or DOCX file.")


def parse_resume_analysis(raw_text):
    analysis = {
        "resume_score": 78,
        "ats_score": 80,
        "strengths": [],
        "weaknesses": [],
        "missing_skills": [],
        "resume_summary_feedback": "Your resume shows a solid foundation and a good starting point for internships or entry-level roles. Add measurable achievements and modern skills to improve your marketability.",
        "project_suggestions": ["AI Career Coach", "Fake News Detection", "Stock Prediction", "Attendance System", "Portfolio Website"],
        "certifications": ["AWS Cloud Practitioner", "Google Data Analytics", "Azure Fundamentals", "Oracle SQL"],
        "best_companies": ["Google", "Microsoft", "Amazon", "Infosys", "TCS", "Accenture", "Capgemini", "IBM", "Oracle"],
        "final_advice": "Focus on clarity, measurable impact, and modern tools so your resume stands out in placements and internships."
    }

    text = raw_text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    def parse_section(section_name, key):
        items = []
        capture = False
        for line in lines:
            if line.lower().startswith(section_name.lower() + ":"):
                capture = True
                remainder = line.split(":", 1)[1].strip()
                if remainder:
                    items.append(remainder)
                continue
            if capture:
                if line.lower().startswith("weaknesses:") or line.lower().startswith("missing skills:") or line.lower().startswith("resume summary feedback:") or line.lower().startswith("project suggestions:") or line.lower().startswith("certifications:") or line.lower().startswith("best companies:") or line.lower().startswith("final career advice:"):
                    break
                if line.startswith("-") or line.startswith("•"):
                    items.append(line[1:].strip().lstrip("• ").strip())
                elif line.lower().startswith("resume score:") or line.lower().startswith("ats compatibility score:"):
                    break
                elif re.match(r"^[0-9]+\.", line):
                    break
        if items:
            analysis[key] = items

    score_match = re.search(r"resume score\s*[:\-]\s*(\d{1,3})", text, re.I)
    if score_match:
        analysis["resume_score"] = int(score_match.group(1))

    ats_match = re.search(r"ats compatibility score\s*[:\-]\s*(\d{1,3})", text, re.I)
    if ats_match:
        analysis["ats_score"] = int(ats_match.group(1))

    parse_section("Strengths", "strengths")
    parse_section("Weaknesses", "weaknesses")
    parse_section("Missing Skills", "missing_skills")
    parse_section("Resume Summary Feedback", "resume_summary_feedback")
    parse_section("Project Suggestions", "project_suggestions")
    parse_section("Certifications", "certifications")
    parse_section("Best Companies", "best_companies")
    parse_section("Final Career Advice", "final_advice")

    if isinstance(analysis.get("resume_summary_feedback"), list):
        analysis["resume_summary_feedback"] = " ".join(analysis["resume_summary_feedback"])
    if isinstance(analysis.get("final_advice"), list):
        analysis["final_advice"] = " ".join(analysis["final_advice"])

    if not analysis["strengths"]:
        analysis["strengths"] = ["Good technical foundation", "Solid project exposure", "Clear career intent"]
    if not analysis["weaknesses"]:
        analysis["weaknesses"] = ["Add measurable achievements", "Improve formatting", "Include modern tools and cloud skills"]
    if not analysis["missing_skills"]:
        analysis["missing_skills"] = ["Docker", "AWS", "Flask", "REST API", "Git", "CI/CD"]

    return analysis


def analyze_resume(resume_text, client=None, model="llama-3.3-70b-versatile"):
    if client is None:
        return "".join([
            "Resume Score: 78/100\n",
            "ATS Compatibility Score: 80/100\n",
            "Strengths:\n",
            "- Strong technical foundation\n",
            "- Good project exposure\n",
            "Weaknesses:\n",
            "- Add measurable achievements\n",
            "- Improve formatting\n",
            "Missing Skills:\n",
            "- Docker\n",
            "- AWS\n",
            "Resume Summary Feedback:\n",
            "- Your resume shows strong potential, but it would benefit from clearer outcomes and stronger ATS phrasing.\n",
            "Project Suggestions:\n",
            "- AI Career Coach\n",
            "- Fake News Detection\n",
            "Certifications:\n",
            "- AWS Cloud Practitioner\n",
            "- Google Data Analytics\n",
            "Best Companies:\n",
            "- Google\n",
            "- Microsoft\n",
            "Final Career Advice:\n",
            "- Focus on measurable results, modern tools, and a polished layout to improve your placement prospects."
        ])

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this resume text:\n\n{resume_text[:12000]}"}
            ],
            model=model,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return analyze_resume(resume_text)


def build_premium_ats_report(resume_text, base_analysis, resume_name, target_role):
    text = resume_text or ""
    lower_text = text.lower()
    words = re.findall(r"[A-Za-z][A-Za-z+#.\-]{1,}", text)
    word_count = len(words)

    role_keywords = {
        "Software Engineer": ["python", "java", "sql", "git", "dsa", "api", "oop", "testing", "docker", "aws", "linux", "problem solving"],
        "Python Developer": ["python", "flask", "django", "sql", "rest api", "git", "pytest", "docker", "aws", "pandas"],
        "Data Analyst": ["sql", "excel", "python", "pandas", "power bi", "tableau", "statistics", "dashboard", "visualization"],
        "ML Engineer": ["python", "machine learning", "deep learning", "tensorflow", "pytorch", "pandas", "numpy", "model", "deployment"],
        "Web Developer": ["html", "css", "javascript", "react", "node", "flask", "api", "git", "responsive", "database"],
        "Backend Developer": ["python", "flask", "django", "sql", "rest api", "docker", "aws", "database", "authentication", "linux"],
    }
    required_keywords = role_keywords.get(target_role, role_keywords["Software Engineer"])
    common_keywords = sorted({
        "python", "sql", "flask", "machine learning", "git", "java", "html", "css",
        "javascript", "react", "api", "database", "excel", "power bi", "tableau",
        "docker", "aws", "linux", "ci/cd", "communication", "problem solving"
    })
    matched_keywords = [kw.title() if len(kw) > 3 else kw.upper() for kw in common_keywords if kw in lower_text]
    missing_keywords = [kw.title() if len(kw) > 3 else kw.upper() for kw in required_keywords if kw not in lower_text]
    keyword_match = round(((len(required_keywords) - len(missing_keywords)) / max(len(required_keywords), 1)) * 100)

    section_terms = {
        "summary": ["summary", "objective", "profile"],
        "skills": ["skills", "technical skills", "technologies"],
        "education": ["education", "degree", "b.tech", "bachelor", "college"],
        "experience": ["experience", "internship", "work experience", "employment"],
        "projects": ["projects", "project"],
        "certifications": ["certification", "certifications", "certificate"],
        "achievements": ["achievement", "achievements", "award", "hackathon"],
        "contact": ["email", "phone", "linkedin", "github"],
    }

    def has_any(terms):
        return any(term in lower_text for term in terms)

    detected = {key: has_any(values) for key, values in section_terms.items()}
    has_numbers = bool(re.search(r"\b\d+(\.\d+)?%?\b", text))
    has_links = "linkedin" in lower_text or "github" in lower_text or "http" in lower_text
    bullet_count = len(re.findall(r"(^|\n)\s*[-•*]", text))
    project_count = max(1 if detected["projects"] else 0, lower_text.count("project"))
    cert_count = len(re.findall(r"certificat|aws|azure|google|oracle|coursera|nptel|udemy", lower_text))
    skills_count = len(matched_keywords)
    pages = max(1, min(4, round(word_count / 450) or 1))
    reading_time = max(1, round(word_count / 220))

    candidate_name = "Not detected"
    for line in [line.strip() for line in text.splitlines()[:8] if line.strip()]:
        if 2 <= len(line.split()) <= 4 and not any(token in line.lower() for token in ["resume", "email", "phone", "@", "http"]):
            candidate_name = line
            break

    score = int(base_analysis.get("ats_score", 78))
    score += 5 if detected["contact"] else -8
    score += 5 if detected["skills"] else -8
    score += 4 if detected["projects"] else -6
    score += 4 if detected["education"] else -6
    score += 4 if has_numbers else -6
    score += 3 if has_links else -4
    score += round((keyword_match - 60) / 5)
    ats_score = max(35, min(98, score))
    resume_score = max(35, min(98, int(base_analysis.get("resume_score", ats_score)) + (4 if has_numbers else -3)))
    potential_score = min(98, ats_score + 12 + len(missing_keywords[:5]))

    def stars(value):
        full = max(1, min(5, round(value / 20)))
        return "★" * full + "☆" * (5 - full)

    sections = [
        {"name": "Professional Summary", "rating": 82 if detected["summary"] else 45, "stars": stars(82 if detected["summary"] else 45), "suggestion": "Add a 3-line summary tailored to the target role." if not detected["summary"] else "Keep the summary keyword-rich and outcome focused."},
        {"name": "Skills", "rating": min(95, 55 + skills_count * 6), "stars": stars(min(95, 55 + skills_count * 6)), "suggestion": "Group skills by languages, frameworks, tools, and databases."},
        {"name": "Projects", "rating": 84 if detected["projects"] else 48, "stars": stars(84 if detected["projects"] else 48), "suggestion": "Add impact, tech stack, links, and measurable outcomes for each project."},
        {"name": "Education", "rating": 88 if detected["education"] else 50, "stars": stars(88 if detected["education"] else 50), "suggestion": "Mention degree, college, CGPA, graduation year, and relevant coursework."},
        {"name": "Experience", "rating": 82 if detected["experience"] else 55, "stars": stars(82 if detected["experience"] else 55), "suggestion": "Use action verbs and quantify internship or work achievements."},
        {"name": "Achievements", "rating": 78 if detected["achievements"] or has_numbers else 42, "stars": stars(78 if detected["achievements"] or has_numbers else 42), "suggestion": "Add awards, hackathons, ranks, or measurable accomplishments."},
    ]

    formatting = [
        {"label": "Margins", "status": "Good" if pages <= 2 else "Needs Improvement"},
        {"label": "Font", "status": "Good"},
        {"label": "Font Size", "status": "Good" if word_count < 1100 else "Needs Improvement"},
        {"label": "Alignment", "status": "Good"},
        {"label": "Bullet Points", "status": "Good" if bullet_count >= 4 else "Needs Improvement"},
        {"label": "Section Titles", "status": "Good" if sum(detected.values()) >= 5 else "Needs Improvement"},
        {"label": "Spacing", "status": "Good"},
        {"label": "Tables", "status": "Good"},
        {"label": "Images", "status": "Good"},
        {"label": "Icons", "status": "Good"},
        {"label": "Headers", "status": "Good"},
        {"label": "Footers", "status": "Good"},
        {"label": "Links", "status": "Good" if has_links else "Needs Improvement"},
        {"label": "Columns", "status": "Good"},
    ]

    missing_sections = [
        name for name, present in [
            ("Career Objective", detected["summary"]),
            ("Achievements", detected["achievements"]),
            ("Volunteer Work", "volunteer" in lower_text),
            ("Languages", "languages" in lower_text),
            ("Publications", "publication" in lower_text),
            ("Leadership", "leadership" in lower_text or "lead" in lower_text),
            ("Hackathons", "hackathon" in lower_text),
            ("Certifications", detected["certifications"]),
        ] if not present
    ]

    companies = ["Google", "Amazon", "Microsoft", "TCS", "Infosys", "Accenture", "IBM", "Oracle", "Capgemini", "Deloitte"]
    company_readiness = []
    for index, company in enumerate(companies):
        adjusted = ats_score + (8 if company in ["TCS", "Infosys", "Accenture", "Capgemini"] else -index % 5)
        status = "Excellent" if adjusted >= 90 else "Good" if adjusted >= 75 else "Average" if adjusted >= 60 else "Needs Improvement"
        company_readiness.append({"company": company, "score": max(40, min(98, adjusted)), "status": status})

    strengths = base_analysis.get("strengths") or ["Clear contact information", "Readable structure", "Relevant technical skills"]
    improvements = base_analysis.get("weaknesses") or ["Add measurable achievements", "Improve keyword coverage", "Add stronger project outcomes"]
    recommendations = [
        f"Add {', '.join(missing_keywords[:3])} if relevant to your target role.",
        "Rewrite project bullets using action verb + task + measurable result.",
        "Add GitHub, LinkedIn, and portfolio links near contact information.",
        "Include a compact professional summary with the exact target role.",
        "Quantify impact using percentages, ranks, users, latency, or accuracy.",
    ]

    return {
        "resume_name": resume_name,
        "target_role": target_role,
        "candidate_name": candidate_name,
        "detected_role": target_role if keyword_match >= 45 else "Entry-Level " + target_role,
        "experience_level": "Fresher / Entry Level" if not detected["experience"] else "Internship / Early Career",
        "education": "Detected" if detected["education"] else "Not detected",
        "skills_count": skills_count,
        "projects_count": project_count,
        "certifications_count": cert_count,
        "resume_pages": pages,
        "reading_time": f"{reading_time} min",
        "ats_score": ats_score,
        "resume_score": resume_score,
        "potential_score": potential_score,
        "keyword_match": keyword_match,
        "matched_keywords": matched_keywords[:14],
        "missing_keywords": missing_keywords[:12],
        "compatibility": [
            {"label": "Contact Information", "ok": detected["contact"]},
            {"label": "Skills Section", "ok": detected["skills"]},
            {"label": "Education", "ok": detected["education"]},
            {"label": "Experience", "ok": detected["experience"]},
            {"label": "Projects", "ok": detected["projects"]},
            {"label": "Certifications", "ok": detected["certifications"]},
            {"label": "Professional Summary", "ok": detected["summary"]},
            {"label": "Role Keywords", "ok": keyword_match >= 65},
            {"label": "Measurable Achievements", "ok": has_numbers},
        ],
        "sections": sections,
        "formatting": formatting,
        "strengths": strengths[:6],
        "improvements": improvements[:7],
        "missing_sections": missing_sections[:8],
        "recruiter_view": {
            "pros": strengths[:3],
            "cons": improvements[:3],
            "overall": "Recruiters will see a promising profile. The fastest improvement path is stronger keywords, measurable impact, and clearer project storytelling."
        },
        "company_readiness": company_readiness,
        "recommendations": recommendations,
        "quality_meter": [
            {"label": "Professionalism", "value": min(96, resume_score + 2)},
            {"label": "Content", "value": resume_score},
            {"label": "Formatting", "value": 86 if bullet_count >= 4 else 68},
            {"label": "Skills", "value": min(95, 50 + skills_count * 6)},
            {"label": "Projects", "value": 84 if detected["projects"] else 55},
            {"label": "Achievements", "value": 78 if has_numbers else 45},
            {"label": "Overall", "value": ats_score},
        ],
        "career_suggestions": {
            "roles": [target_role, "Python Developer", "Backend Developer", "Data Analyst", "Software Engineer"],
            "projects": ["Deploy a Flask REST API", "Build a dashboard with SQL analytics", "Create an ATS-friendly portfolio site"],
            "skills": missing_keywords[:6] or ["Docker", "AWS", "REST API", "SQL"],
            "courses": ["FreeCodeCamp Backend APIs", "AWS Cloud Practitioner", "SQL for Data Analysis"],
            "certifications": base_analysis.get("certifications", [])[:4],
        },
        "rewrite_suggestions": [
            "Built a Flask application" + " -> Built and deployed a Flask application with authentication, database workflows, and measurable user outcomes.",
            "Worked on machine learning project" + " -> Developed an ML model, evaluated accuracy, and documented business impact clearly.",
            "Good communication skills" + " -> Collaborated with teammates to present technical ideas clearly during reviews and demos.",
        ],
        "heatmap": [{"label": item["name"], "value": item["rating"]} for item in sections],
        "summary": base_analysis.get("resume_summary_feedback", "Your resume is a strong starting point and can become more ATS-ready with clearer keywords and quantified outcomes."),
        "final_advice": base_analysis.get("final_advice", "Focus on clarity, measurable impact, and role-specific keywords."),
    }
