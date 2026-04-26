"""
AI-powered job matching — scores each job against the user's profile.

Uses OpenAI API (or compatible) to:
1. Score relevance (0-100)
2. Explain why the job matches
3. Flag visa/eligibility concerns
4. Suggest application strategy
"""

import json
import os
import time
from typing import Optional

import openai

from core.database import get_jobs, update_job_score, get_job


def get_client():
    """Get OpenAI client with configured API key."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL")  # For compatible APIs
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set. Add it in Settings.")
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return openai.OpenAI(**kwargs)


def load_profile() -> dict:
    """Load user profile from data/profile.json."""
    profile_path = os.environ.get("PROFILE_PATH", "data/profile.json")
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            return json.load(f)
    return {}


def build_profile_summary(profile: dict) -> str:
    """Build a concise profile summary for the AI."""
    parts = []
    parts.append(f"Name: {profile.get('name', 'N/A')}")
    parts.append(f"Target roles: {', '.join(profile.get('target_roles', []))}")
    parts.append(f"Education: {profile.get('education', 'N/A')}")
    parts.append(f"Research areas: {', '.join(profile.get('research_areas', []))}")
    parts.append(f"Skills: {', '.join(profile.get('skills', []))}")
    parts.append(f"Experience highlights: {profile.get('experience_summary', 'N/A')}")
    parts.append(f"Publications: {profile.get('publications_summary', 'N/A')}")
    parts.append(f"Visa status: {profile.get('visa_status', 'N/A')}")
    parts.append(f"Preferred locations: {', '.join(profile.get('preferred_locations', ['Any']))}")
    parts.append(f"Min salary: {profile.get('min_salary', 'Flexible')}")
    return "\n".join(parts)


def score_job(job: dict, profile: dict, client=None) -> dict:
    """
    Score a single job against the profile using AI.

    Returns:
        dict with keys: score (0-100), reasoning, visa_concern, strategy
    """
    if client is None:
        client = get_client()

    profile_summary = build_profile_summary(profile)
    model = os.environ.get("MATCHER_MODEL", "gpt-4o-mini")

    job_text = f"""
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Type: {job.get('job_type', 'N/A')}
Salary: {job.get('salary_min', '?')} - {job.get('salary_max', '?')}
Source: {job.get('source', 'N/A')}
Description: {(job.get('description', '') or '')[:3000]}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """You are an expert career advisor. Score how well a job matches a candidate's profile.

Return a JSON object with exactly these fields:
{
    "score": <integer 0-100>,
    "reasoning": "<2-3 sentence explanation of the match>",
    "visa_concern": "<none|low|medium|high — likelihood of visa sponsorship issues>",
    "strategy": "<1 sentence application tip>",
    "match_highlights": ["<key matching qualification 1>", "<key matching qualification 2>"],
    "gaps": ["<missing requirement 1>", "<missing requirement 2>"]
}

Scoring guidelines:
- 90-100: Perfect match — role, skills, research area, and level all align
- 75-89: Strong match — most requirements met, minor gaps
- 60-74: Good match — solid foundation but some missing qualifications
- 40-59: Partial match — worth considering but significant gaps
- 20-39: Weak match — stretch application
- 0-19: Poor match — don't bother

Consider: research fit, skill overlap, career level, location, visa friendliness, and career trajectory."""
            },
            {
                "role": "user",
                "content": f"CANDIDATE PROFILE:\n{profile_summary}\n\nJOB LISTING:\n{job_text}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=500,
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "score": max(0, min(100, int(result.get("score", 0)))),
            "reasoning": result.get("reasoning", ""),
            "visa_concern": result.get("visa_concern", "unknown"),
            "strategy": result.get("strategy", ""),
            "match_highlights": result.get("match_highlights", []),
            "gaps": result.get("gaps", []),
        }
    except (json.JSONDecodeError, ValueError):
        return {"score": 0, "reasoning": "Failed to parse AI response", "visa_concern": "unknown", "strategy": ""}


def score_unscored_jobs(limit: int = 50, min_description_length: int = 50) -> int:
    """
    Score all unscored jobs in the database.

    Returns number of jobs scored.
    """
    profile = load_profile()
    if not profile:
        print("[matcher] No profile found — cannot score jobs")
        return 0

    jobs = get_jobs(limit=limit)
    unscored = [j for j in jobs if j["match_score"] == 0 and len(j.get("description", "") or "") >= min_description_length]

    if not unscored:
        print("[matcher] No unscored jobs to process")
        return 0

    client = get_client()
    scored = 0

    for job in unscored:
        try:
            result = score_job(job, profile, client)
            reasoning = result["reasoning"]
            if result.get("visa_concern") and result["visa_concern"] != "none":
                reasoning += f"\n⚠️ Visa concern: {result['visa_concern']}"
            if result.get("strategy"):
                reasoning += f"\n💡 Strategy: {result['strategy']}"
            if result.get("match_highlights"):
                reasoning += f"\n✅ Highlights: {', '.join(result['match_highlights'])}"
            if result.get("gaps"):
                reasoning += f"\n⚠️ Gaps: {', '.join(result['gaps'])}"

            update_job_score(job["id"], result["score"], reasoning)
            scored += 1
            print(f"[matcher] {job['title']} @ {job['company']} → {result['score']}/100")
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            print(f"[matcher] Error scoring job {job['id']}: {e}")

    return scored


def rescore_job(job_id: int) -> Optional[dict]:
    """Rescore a specific job."""
    job = get_job(job_id)
    if not job:
        return None

    profile = load_profile()
    result = score_job(job, profile)
    reasoning = result["reasoning"]
    update_job_score(job_id, result["score"], reasoning)
    return result
