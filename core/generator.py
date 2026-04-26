"""
AI-powered application material generator.

Generates tailored cover letters and resume summaries for each job,
using the candidate's profile and the job description.
"""

import json
import os
from typing import Optional

import openai

from core.database import get_job, create_application, update_application
from core.matcher import load_profile, get_client, build_profile_summary


def generate_cover_letter(job_id: int, style: str = "professional") -> str:
    """
    Generate a tailored cover letter for a specific job.

    Args:
        job_id: Database ID of the job
        style: 'professional', 'academic', or 'startup'

    Returns:
        Generated cover letter text
    """
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    profile = load_profile()
    profile_summary = build_profile_summary(profile)
    client = get_client()
    model = os.environ.get("GENERATOR_MODEL", "gpt-4o-mini")

    style_instructions = {
        "professional": "Write a professional, polished cover letter suitable for a corporate AI/ML position. Be confident but not arrogant. Quantify achievements where possible.",
        "academic": "Write an academic cover letter suitable for a tenure-track faculty position. Emphasize research vision, teaching philosophy, and publication record. Reference specific departmental fit.",
        "startup": "Write an energetic, concise cover letter for a fast-paced tech company. Focus on impact, shipping products, and adaptability. Keep it under 400 words.",
    }

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": f"""You are an expert career consultant who writes compelling, personalized cover letters.

{style_instructions.get(style, style_instructions['professional'])}

Rules:
- Address the specific role and company — show you've researched them
- Connect the candidate's experience directly to job requirements
- Include 2-3 specific, quantified achievements
- Show enthusiasm for the company's mission
- Keep it to 3-4 paragraphs (under 500 words for industry, under 700 for academic)
- Do NOT use generic filler phrases
- Do NOT start with "I am writing to apply for..."
- Make every sentence earn its place
- If visa status is relevant, mention OPT/STEM OPT eligibility briefly and positively"""
            },
            {
                "role": "user",
                "content": f"""CANDIDATE PROFILE:
{profile_summary}

FULL BACKGROUND:
{json.dumps(profile.get('detailed_background', {}), indent=2) if profile.get('detailed_background') else 'See profile summary above.'}

JOB DETAILS:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Description: {(job.get('description', '') or '')[:4000]}

Generate a tailored cover letter for this position."""
            }
        ],
        temperature=0.7,
        max_tokens=1500,
    )

    return response.choices[0].message.content


def generate_resume_bullets(job_id: int) -> str:
    """
    Generate tailored resume bullet points for a specific job.
    Suggests which experiences to emphasize and how to phrase them.
    """
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    profile = load_profile()
    client = get_client()
    model = os.environ.get("GENERATOR_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """You are a resume optimization expert. Given a candidate's profile and a job listing,
suggest how to tailor the resume. Output:

1. SUMMARY: A tailored 2-3 sentence professional summary
2. KEY SKILLS TO HIGHLIGHT: Top 8 skills to feature prominently
3. EXPERIENCE BULLETS: 5-6 tailored bullet points emphasizing relevant experience
4. PUBLICATIONS TO FEATURE: Which publications to highlight and why
5. KEYWORDS TO ADD: Important keywords from the job description to include

Be specific and actionable. Use strong action verbs. Quantify where possible."""
            },
            {
                "role": "user",
                "content": f"""CANDIDATE: {build_profile_summary(profile)}

JOB:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Description: {(job.get('description', '') or '')[:4000]}"""
            }
        ],
        temperature=0.5,
        max_tokens=1200,
    )

    return response.choices[0].message.content


def generate_application_email(job_id: int) -> str:
    """Generate an email for positions that accept email applications."""
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    profile = load_profile()
    client = get_client()
    model = os.environ.get("GENERATOR_MODEL", "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """Write a brief, professional application email. Include:
- Clear subject line (format: "Application: [Title] — [Your Name]")
- 2-3 paragraph body that highlights fit
- Mention attached CV and cover letter
- Professional closing

Keep it concise — the cover letter has the details. The email just needs to make them open the attachment."""
            },
            {
                "role": "user",
                "content": f"""CANDIDATE: {profile.get('name', 'Candidate')} — {profile.get('education', '')}

JOB:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}

Generate the email."""
            }
        ],
        temperature=0.6,
        max_tokens=500,
    )

    return response.choices[0].message.content


def generate_and_save(job_id: int, style: str = "professional") -> int:
    """
    Generate all materials for a job and save as an application.

    Returns application ID.
    """
    # Determine style based on job source/type
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    if job.get("source") == "HigherEdJobs" or "professor" in (job.get("title", "")).lower():
        style = "academic"
    elif any(kw in (job.get("company", "")).lower() for kw in ["startup", "seed", "series a"]):
        style = "startup"

    cover_letter = generate_cover_letter(job_id, style=style)
    app_id = create_application(job_id, cover_letter=cover_letter)
    return app_id
