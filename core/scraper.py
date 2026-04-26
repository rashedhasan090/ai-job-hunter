"""
Multi-source job scraper — aggregates jobs from multiple APIs and websites.

Supported sources:
  - SerpAPI (Google Jobs) — best coverage, needs API key
  - Adzuna — structured data, free tier
  - Remotive — remote tech jobs, no key needed
  - Arbeitnow — remote/hybrid, no key needed
  - USAJobs — government positions, free
  - HigherEdJobs — academic positions (web scrape)
  - LinkedIn (via SerpAPI) — if enabled
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from core.database import upsert_job, log_search


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_id(source: str, *parts) -> str:
    """Generate a deterministic external_id."""
    raw = f"{source}:{'|'.join(str(p) for p in parts)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator="\n").strip()


def _safe_request(url, params=None, headers=None, timeout=30):
    """Safe HTTP GET with retries."""
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt == 2:
                print(f"[scraper] Request failed after 3 attempts: {e}")
                return None
            time.sleep(1)
    return None


# ── SerpAPI (Google Jobs) ────────────────────────────────────────────────

def scrape_serpapi(queries: list[str], location: str = "United States",
                   api_key: str = None, max_per_query: int = 20) -> list[dict]:
    """Scrape Google Jobs via SerpAPI."""
    api_key = api_key or os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        print("[serpapi] No API key — skipping")
        return []

    all_jobs = []
    for query in queries:
        resp = _safe_request("https://serpapi.com/search.json", params={
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": api_key,
            "num": max_per_query,
        })
        if not resp:
            continue

        data = resp.json()
        jobs = data.get("jobs_results", [])
        for j in jobs:
            job = {
                "external_id": _make_id("serpapi", j.get("job_id", j.get("title", ""))),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "description": j.get("description", ""),
                "url": j.get("share_link") or j.get("related_links", [{}])[0].get("link", ""),
                "source": "Google Jobs",
                "job_type": ", ".join(j.get("detected_extensions", {}).get("schedule_type", "").split()),
                "posted_date": j.get("detected_extensions", {}).get("posted_at", ""),
                "remote": "remote" in j.get("location", "").lower(),
                "tags": j.get("job_highlights", []),
                "raw_data": j,
            }

            # Extract salary if present
            salary = j.get("detected_extensions", {})
            if salary.get("salary"):
                sal_text = salary["salary"]
                numbers = re.findall(r'[\d,]+', sal_text.replace(",", ""))
                if len(numbers) >= 2:
                    job["salary_min"] = float(numbers[0])
                    job["salary_max"] = float(numbers[1])
                elif len(numbers) == 1:
                    job["salary_min"] = float(numbers[0])

            all_jobs.append(job)

        log_search(query, "serpapi", len(jobs))
        time.sleep(0.5)  # Rate limit

    return all_jobs


# ── Adzuna ───────────────────────────────────────────────────────────────

def scrape_adzuna(queries: list[str], location: str = "us",
                  app_id: str = None, app_key: str = None,
                  max_per_query: int = 20) -> list[dict]:
    """Scrape jobs from Adzuna API."""
    app_id = app_id or os.environ.get("ADZUNA_APP_ID", "")
    app_key = app_key or os.environ.get("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        print("[adzuna] No API credentials — skipping")
        return []

    all_jobs = []
    for query in queries:
        resp = _safe_request(
            f"https://api.adzuna.com/v1/api/jobs/{location}/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "results_per_page": max_per_query,
                "content-type": "application/json",
            }
        )
        if not resp:
            continue

        data = resp.json()
        for j in data.get("results", []):
            job = {
                "external_id": _make_id("adzuna", j.get("id", j.get("title", ""))),
                "title": j.get("title", ""),
                "company": j.get("company", {}).get("display_name", ""),
                "location": j.get("location", {}).get("display_name", ""),
                "description": _clean_html(j.get("description", "")),
                "url": j.get("redirect_url", ""),
                "source": "Adzuna",
                "job_type": j.get("contract_type", ""),
                "salary_min": j.get("salary_min"),
                "salary_max": j.get("salary_max"),
                "posted_date": j.get("created", ""),
                "remote": "remote" in j.get("title", "").lower() or "remote" in j.get("description", "").lower(),
                "raw_data": j,
            }
            all_jobs.append(job)

        log_search(query, "adzuna", len(data.get("results", [])))
        time.sleep(0.3)

    return all_jobs


# ── Remotive (Free, no key) ─────────────────────────────────────────────

def scrape_remotive(queries: list[str], max_per_query: int = 20) -> list[dict]:
    """Scrape remote jobs from Remotive.com (free, no API key)."""
    all_jobs = []
    for query in queries:
        resp = _safe_request("https://remotive.com/api/remote-jobs", params={
            "search": query,
            "limit": max_per_query,
        })
        if not resp:
            continue

        data = resp.json()
        for j in data.get("jobs", []):
            job = {
                "external_id": _make_id("remotive", j.get("id", "")),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Worldwide"),
                "description": _clean_html(j.get("description", "")),
                "url": j.get("url", ""),
                "source": "Remotive",
                "job_type": j.get("job_type", ""),
                "posted_date": j.get("publication_date", ""),
                "remote": True,
                "salary_min": j.get("salary") if isinstance(j.get("salary"), (int, float)) else None,
                "tags": [j.get("category", "")],
                "raw_data": j,
            }
            all_jobs.append(job)

        log_search(query, "remotive", len(data.get("jobs", [])))
        time.sleep(0.3)

    return all_jobs


# ── Arbeitnow (Free, no key) ────────────────────────────────────────────

def scrape_arbeitnow(queries: list[str], max_per_query: int = 20) -> list[dict]:
    """Scrape jobs from Arbeitnow (free API)."""
    all_jobs = []
    # Arbeitnow doesn't support search queries directly, so we fetch and filter
    resp = _safe_request("https://www.arbeitnow.com/api/job-board-api")
    if not resp:
        return []

    data = resp.json()
    all_listings = data.get("data", [])

    for query in queries:
        query_lower = query.lower()
        matched = [
            j for j in all_listings
            if query_lower in j.get("title", "").lower()
            or query_lower in j.get("description", "").lower()
            or any(query_lower in tag.lower() for tag in j.get("tags", []))
        ][:max_per_query]

        for j in matched:
            job = {
                "external_id": _make_id("arbeitnow", j.get("slug", j.get("title", ""))),
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "description": _clean_html(j.get("description", "")),
                "url": j.get("url", ""),
                "source": "Arbeitnow",
                "job_type": j.get("job_types", [""])[0] if j.get("job_types") else "",
                "posted_date": j.get("created_at", ""),
                "remote": j.get("remote", False),
                "tags": j.get("tags", []),
                "raw_data": j,
            }
            all_jobs.append(job)

        log_search(query, "arbeitnow", len(matched))

    return all_jobs


# ── USAJobs (Free, needs API key — free registration) ───────────────────

def scrape_usajobs(queries: list[str], api_key: str = None,
                   email: str = None, max_per_query: int = 20) -> list[dict]:
    """Scrape government jobs from USAJobs.gov."""
    api_key = api_key or os.environ.get("USAJOBS_API_KEY", "")
    email = email or os.environ.get("USAJOBS_EMAIL", "")
    if not api_key or not email:
        print("[usajobs] No API credentials — skipping")
        return []

    all_jobs = []
    headers = {
        "Authorization-Key": api_key,
        "User-Agent": email,
        "Host": "data.usajobs.gov",
    }

    for query in queries:
        resp = _safe_request(
            "https://data.usajobs.gov/api/search",
            params={"Keyword": query, "ResultsPerPage": max_per_query},
            headers=headers,
        )
        if not resp:
            continue

        data = resp.json()
        items = data.get("SearchResult", {}).get("SearchResultItems", [])
        for item in items:
            j = item.get("MatchedObjectDescriptor", {})
            pos = j.get("PositionLocation", [{}])[0] if j.get("PositionLocation") else {}
            salary = j.get("PositionRemuneration", [{}])[0] if j.get("PositionRemuneration") else {}

            job = {
                "external_id": _make_id("usajobs", j.get("PositionID", "")),
                "title": j.get("PositionTitle", ""),
                "company": j.get("OrganizationName", ""),
                "location": pos.get("CityName", "") + ", " + pos.get("CountrySubDivisionCode", ""),
                "description": _clean_html(j.get("QualificationSummary", "")),
                "url": j.get("PositionURI", ""),
                "source": "USAJobs",
                "job_type": j.get("PositionSchedule", [{}])[0].get("Name", "") if j.get("PositionSchedule") else "",
                "salary_min": float(salary.get("MinimumRange", 0)) if salary.get("MinimumRange") else None,
                "salary_max": float(salary.get("MaximumRange", 0)) if salary.get("MaximumRange") else None,
                "posted_date": j.get("PositionStartDate", ""),
                "deadline": j.get("ApplicationCloseDate", ""),
                "raw_data": j,
            }
            all_jobs.append(job)

        log_search(query, "usajobs", len(items))
        time.sleep(0.3)

    return all_jobs


# ── Academic Jobs (Web Scraping) ─────────────────────────────────────────

def scrape_higheredjobs(queries: list[str], max_per_query: int = 15) -> list[dict]:
    """Scrape academic positions from HigherEdJobs."""
    all_jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    for query in queries:
        resp = _safe_request(
            f"https://www.higheredjobs.com/search/default.cfm",
            params={"JobCat": "64", "keyword": query, "PosType": "1"},  # 64=CS, 1=Faculty
            headers=headers,
        )
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.row.record, div.listing-item, tr.job-listing")[:max_per_query]

        for listing in listings:
            title_el = listing.select_one("a[href*='details.cfm']") or listing.select_one("a.job-title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = title_el.get("href", "")
            if url and not url.startswith("http"):
                url = "https://www.higheredjobs.com" + url

            company_el = listing.select_one("span.institution, td.institution, div.employer")
            location_el = listing.select_one("span.location, td.location, div.location")

            job = {
                "external_id": _make_id("higheredjobs", url or title),
                "title": title,
                "company": company_el.get_text(strip=True) if company_el else "",
                "location": location_el.get_text(strip=True) if location_el else "",
                "description": "",
                "url": url,
                "source": "HigherEdJobs",
                "job_type": "Faculty / Tenure-Track",
                "remote": False,
                "raw_data": {},
            }
            all_jobs.append(job)

        log_search(query, "higheredjobs", len(listings))
        time.sleep(1)  # Be polite

    return all_jobs


# ── Master Scraper ───────────────────────────────────────────────────────

def scrape_all(queries: list[str], sources: Optional[list[str]] = None,
               location: str = "United States") -> dict:
    """
    Run all enabled scrapers and upsert results into the database.

    Returns:
        dict with source names as keys and job counts as values.
    """
    if sources is None:
        sources = ["serpapi", "adzuna", "remotive", "arbeitnow", "usajobs", "higheredjobs"]

    results = {}
    all_jobs = []

    source_map = {
        "serpapi": lambda: scrape_serpapi(queries, location=location),
        "adzuna": lambda: scrape_adzuna(queries),
        "remotive": lambda: scrape_remotive(queries),
        "arbeitnow": lambda: scrape_arbeitnow(queries),
        "usajobs": lambda: scrape_usajobs(queries),
        "higheredjobs": lambda: scrape_higheredjobs(queries),
    }

    for source in sources:
        if source in source_map:
            try:
                print(f"[scraper] Scraping {source}...")
                jobs = source_map[source]()
                results[source] = len(jobs)
                all_jobs.extend(jobs)
                print(f"[scraper] {source}: {len(jobs)} jobs found")
            except Exception as e:
                print(f"[scraper] {source} error: {e}")
                results[source] = 0

    # Upsert all jobs
    new_count = 0
    for job in all_jobs:
        try:
            upsert_job(job)
            new_count += 1
        except Exception as e:
            print(f"[scraper] Failed to save job: {e}")

    results["total_saved"] = new_count
    return results
