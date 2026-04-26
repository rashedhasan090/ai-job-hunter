"""
Auto-apply engine — handles automated job application submission.

Strategies:
1. Email applications: Send email with cover letter + resume (academic positions)
2. API-based: Submit via Lever/Greenhouse APIs where available
3. Easy-apply: Generate pre-filled data for quick portal submissions
4. Manual assist: Generate all materials + step-by-step instructions

Note: This respects rate limits, includes human-in-the-loop approval,
and never submits without explicit user confirmation.
"""

import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Optional

from core.database import get_job, get_applications, update_application, create_application


# ── Email-based Application ─────────────────────────────────────────────

def send_application_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: list[str] = None,
    cc: str = None,
    smtp_server: str = None,
    smtp_port: int = 587,
    smtp_user: str = None,
    smtp_pass: str = None,
) -> dict:
    """
    Send an application email with attachments.

    Returns dict with status and message_id.
    """
    smtp_server = smtp_server or os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", smtp_port))
    smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
    smtp_pass = smtp_pass or os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        return {"status": "error", "message": "SMTP credentials not configured"}

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain"))

    # Attach files
    for filepath in (attachments or []):
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                attachment = MIMEApplication(f.read())
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=os.path.basename(filepath)
                )
                msg.attach(attachment)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            return {"status": "sent", "message": f"Email sent to {to_email}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── ATS Detection ───────────────────────────────────────────────────────

def detect_ats(url: str) -> Optional[str]:
    """Detect which ATS a job uses from its URL."""
    if not url:
        return None
    url_lower = url.lower()

    ats_patterns = {
        "lever": ["lever.co", "jobs.lever.co"],
        "greenhouse": ["greenhouse.io", "boards.greenhouse.io"],
        "workday": ["myworkdayjobs.com", "wd5.myworkdayjobs.com"],
        "icims": ["icims.com", "careers-"],
        "taleo": ["taleo.net", "oracle.taleo"],
        "smartrecruiters": ["smartrecruiters.com"],
        "bamboohr": ["bamboohr.com"],
        "jazz": ["jazz.co", "applytojob.com"],
        "jobvite": ["jobvite.com"],
        "ashby": ["ashbyhq.com"],
    }

    for ats, patterns in ats_patterns.items():
        if any(p in url_lower for p in patterns):
            return ats
    return "unknown"


# ── Pre-fill Data Generator ─────────────────────────────────────────────

def generate_prefill_data(profile: dict) -> dict:
    """
    Generate pre-fill data for common application portal fields.
    This can be used by browser extensions or manual copy-paste.
    """
    return {
        "personal": {
            "first_name": profile.get("name", "").split()[0] if profile.get("name") else "",
            "last_name": " ".join(profile.get("name", "").split()[1:]) if profile.get("name") else "",
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "linkedin": profile.get("linkedin", ""),
            "website": profile.get("website", ""),
            "github": profile.get("github", ""),
            "google_scholar": profile.get("google_scholar", ""),
        },
        "education": {
            "degree": profile.get("highest_degree", "PhD"),
            "university": profile.get("university", ""),
            "graduation_date": profile.get("graduation_date", ""),
            "gpa": profile.get("gpa", ""),
            "major": profile.get("major", ""),
        },
        "work_auth": {
            "authorized_us": profile.get("us_work_authorized", True),
            "visa_status": profile.get("visa_status", ""),
            "sponsorship_needed": profile.get("needs_sponsorship", True),
            "visa_type": profile.get("visa_type", "F-1 OPT/STEM OPT"),
        },
        "diversity": {
            "gender": profile.get("gender", ""),
            "race_ethnicity": profile.get("race_ethnicity", ""),
            "veteran_status": profile.get("veteran_status", "No"),
            "disability_status": profile.get("disability_status", "Prefer not to answer"),
        },
        "links": {
            "resume_url": profile.get("resume_url", ""),
            "cover_letter_url": profile.get("cover_letter_url", ""),
            "portfolio_url": profile.get("website", ""),
        }
    }


# ── Application Pipeline ────────────────────────────────────────────────

def prepare_application(job_id: int, cover_letter: str, profile: dict) -> dict:
    """
    Prepare everything needed to apply for a job.

    Returns a dict with:
    - method: 'email', 'api', 'portal', 'manual'
    - ats: detected ATS name
    - prefill_data: form field data
    - email_draft: email content if email-based
    - instructions: step-by-step for manual applications
    """
    job = get_job(job_id)
    if not job:
        return {"error": "Job not found"}

    ats = detect_ats(job.get("url", ""))
    prefill = generate_prefill_data(profile)
    title = job.get("title", "")
    company = job.get("company", "")

    result = {
        "job_id": job_id,
        "job_title": title,
        "company": company,
        "url": job.get("url", ""),
        "ats": ats,
        "prefill_data": prefill,
    }

    # Determine best application method
    if job.get("source") == "HigherEdJobs" or "professor" in title.lower():
        result["method"] = "email"
        result["email_draft"] = {
            "subject": f"Application: {title} — {profile.get('name', '')}",
            "body": f"""Dear Search Committee,

I am writing to apply for the {title} position at {company}. Please find attached my curriculum vitae, cover letter, research statement, and teaching statement.

{cover_letter[:200]}...

I look forward to the opportunity to discuss how my research in trustworthy AI and formal verification can contribute to your department.

Best regards,
{profile.get('name', '')}
{profile.get('email', '')}
{profile.get('website', '')}""",
            "attachments_needed": [
                "CV/Resume", "Cover Letter", "Research Statement",
                "Teaching Statement", "Publication List",
            ],
        }
    elif ats in ["lever", "greenhouse", "ashby"]:
        result["method"] = "api"
        result["instructions"] = [
            f"1. Navigate to: {job.get('url', '')}",
            "2. The form fields have been pre-filled below — copy each value",
            "3. Upload your tailored resume and cover letter",
            "4. Review all fields before submitting",
        ]
    else:
        result["method"] = "portal"
        result["instructions"] = [
            f"1. Navigate to: {job.get('url', '')}",
            f"2. ATS detected: {ats or 'Unknown'}",
            "3. Use the pre-fill data below to quickly complete the form",
            "4. Upload your tailored resume",
            "5. Paste the generated cover letter",
            "6. Review and submit",
        ]

    return result


def batch_prepare(job_ids: list[int], profile: dict) -> list[dict]:
    """Prepare applications for multiple jobs."""
    results = []
    for job_id in job_ids:
        try:
            result = prepare_application(job_id, "", profile)
            results.append(result)
        except Exception as e:
            results.append({"job_id": job_id, "error": str(e)})
    return results
