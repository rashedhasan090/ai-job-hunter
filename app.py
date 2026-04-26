"""
🎯 AI Job Hunter — Your intelligent job search autopilot.

An AI-powered application that scrapes jobs, matches them to your profile,
generates tailored materials, and helps you apply at scale.

Author: Built by Viktor AI (getviktor.com)
"""

import json
import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# ── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Job Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize ───────────────────────────────────────────────────────────
from core.database import init_db, get_jobs, get_stats, update_job_status, get_job
from core.database import get_applications, get_setting, set_setting

init_db()

# ── Custom CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp { font-family: 'Inter', sans-serif; }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .metric-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3); }
    .metric-card.orange { background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%); box-shadow: 0 4px 15px rgba(242, 153, 74, 0.3); }
    .metric-card.blue { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3); }
    .metric-card.red { background: linear-gradient(135deg, #f5576c 0%, #ff6b6b 100%); box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3); }
    .metric-value { font-size: 36px; font-weight: 800; margin: 4px 0; }
    .metric-label { font-size: 13px; font-weight: 500; opacity: 0.9; letter-spacing: 0.5px; text-transform: uppercase; }

    /* Score badge */
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 14px;
        color: white;
    }
    .score-high { background: #11998e; }
    .score-medium { background: #F2994A; }
    .score-low { background: #f5576c; }

    /* Job card */
    .job-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        background: white;
        transition: box-shadow 0.2s;
    }
    .job-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

    /* Status badges */
    .status-new { color: #4facfe; }
    .status-interested { color: #667eea; }
    .status-applied { color: #11998e; }
    .status-interviewing { color: #F2994A; }
    .status-offer { color: #38ef7d; }
    .status-rejected { color: #f5576c; }

    /* Hide streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    .block-container { padding-top: 2rem; }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    div[data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar Navigation ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🎯 AI Job Hunter")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "🔍 Job Discovery", "🤖 AI Matching", "📝 Applications",
         "✨ Generate Materials", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick stats
    stats = get_stats()
    st.metric("Total Jobs", stats["total_jobs"])
    st.metric("Top Match", f"{stats['top_match']}%")
    st.metric("Applied", stats["applied"])

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; opacity:0.6; font-size:12px;'>"
        "Built by <a href='https://getviktor.com' style='color:#667eea;'>Viktor AI</a>"
        "</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("## 📊 Dashboard")
    st.markdown("Your job search at a glance.")

    # Metric cards
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Jobs</div>
            <div class="metric-value">{stats['total_jobs']}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card green">
            <div class="metric-label">Top Match</div>
            <div class="metric-value">{stats['top_match']}%</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card orange">
            <div class="metric-label">Interested</div>
            <div class="metric-value">{stats['interested']}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card blue">
            <div class="metric-label">Applied</div>
            <div class="metric-value">{stats['applied']}</div>
        </div>""", unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card red">
            <div class="metric-label">Interviewing</div>
            <div class="metric-value">{stats['interviewing']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Top matches table
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### 🏆 Top Matches")
        top_jobs = get_jobs(min_score=60, limit=10)
        if top_jobs:
            for job in top_jobs:
                score = job["match_score"]
                score_class = "high" if score >= 75 else "medium" if score >= 50 else "low"
                with st.container():
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1:
                        st.markdown(f"**{job['title']}**")
                        st.caption(f"{job['company']} · {job['location'] or 'N/A'}")
                    with c2:
                        st.markdown(
                            f'<span class="score-badge score-{score_class}">{score}%</span>',
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.caption(job["source"])
                    st.divider()
        else:
            st.info("No scored jobs yet. Go to 🔍 Job Discovery to scrape jobs, then 🤖 AI Matching to score them.")

    with col_right:
        st.markdown("### 📈 Sources")
        if stats["sources"]:
            source_df = pd.DataFrame(
                list(stats["sources"].items()),
                columns=["Source", "Jobs"]
            )
            st.bar_chart(source_df.set_index("Source"))
        else:
            st.info("No jobs scraped yet.")

        st.markdown("### 📅 Recent Applications")
        apps = get_applications()[:5]
        if apps:
            for app in apps:
                st.markdown(f"**{app['title']}** @ {app['company']}")
                st.caption(f"Status: {app['status']} · {app.get('applied_at', 'Draft')}")
        else:
            st.info("No applications yet.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Job Discovery
# ══════════════════════════════════════════════════════════════════════════
elif page == "🔍 Job Discovery":
    st.markdown("## 🔍 Job Discovery")
    st.markdown("Search and scrape jobs from multiple sources.")

    from core.scraper import scrape_all

    # Search configuration
    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])

        with col1:
            default_queries = get_setting("search_queries",
                "AI ML Researcher, Machine Learning Scientist, Assistant Professor Computer Science, AI Engineer, Research Scientist AI")
            queries_input = st.text_area(
                "Search Queries (one per line or comma-separated)",
                value=default_queries,
                height=100,
            )

        with col2:
            location = st.text_input("Location", value=get_setting("search_location", "United States"))

            sources = st.multiselect(
                "Sources",
                ["serpapi", "adzuna", "remotive", "arbeitnow", "usajobs", "higheredjobs"],
                default=["remotive", "arbeitnow"],
            )

        submitted = st.form_submit_button("🔍 Search Jobs", use_container_width=True, type="primary")

    if submitted:
        # Parse queries
        queries = [q.strip() for q in queries_input.replace("\n", ",").split(",") if q.strip()]
        set_setting("search_queries", queries_input)
        set_setting("search_location", location)

        with st.spinner(f"Scraping {len(queries)} queries across {len(sources)} sources..."):
            results = scrape_all(queries, sources=sources, location=location)

        st.success(f"✅ Found {results.get('total_saved', 0)} jobs!")

        for source, count in results.items():
            if source != "total_saved":
                st.caption(f"  {source}: {count} jobs")

        st.rerun()

    # Show all jobs
    st.markdown("---")
    st.markdown("### 📋 All Jobs")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        filter_status = st.selectbox("Status", ["All", "new", "interested", "applied", "rejected"])
    with col2:
        filter_source = st.selectbox("Source", ["All"] + list(get_stats().get("sources", {}).keys()))
    with col3:
        filter_score = st.slider("Min Score", 0, 100, 0)

    status_filter = None if filter_status == "All" else filter_status
    source_filter = None if filter_source == "All" else filter_source

    jobs = get_jobs(status=status_filter, source=source_filter, min_score=filter_score, limit=100)

    if jobs:
        for job in jobs:
            with st.expander(
                f"{'⭐' if job['match_score'] >= 75 else '🔵' if job['match_score'] >= 50 else '⚪'} "
                f"**{job['title']}** — {job['company'] or 'Unknown'} "
                f"({'🏠 Remote' if job.get('remote') else job.get('location', 'N/A')}) "
                f"[{job['match_score']:.0f}%]"
            ):
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.markdown(f"**Company:** {job.get('company', 'N/A')}")
                    st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                    st.markdown(f"**Source:** {job.get('source', 'N/A')}")
                    if job.get("salary_min") or job.get("salary_max"):
                        st.markdown(f"**Salary:** ${job.get('salary_min', '?'):,.0f} — ${job.get('salary_max', '?'):,.0f}")
                    if job.get("url"):
                        st.markdown(f"[🔗 Apply Link]({job['url']})")

                with col2:
                    new_status = st.selectbox(
                        "Status",
                        ["new", "interested", "applied", "rejected", "interviewing", "offer"],
                        index=["new", "interested", "applied", "rejected", "interviewing", "offer"].index(job.get("status", "new")),
                        key=f"status_{job['id']}",
                    )
                    if new_status != job.get("status"):
                        update_job_status(job["id"], new_status)
                        st.rerun()

                with col3:
                    score = job["match_score"]
                    score_color = "#11998e" if score >= 75 else "#F2994A" if score >= 50 else "#f5576c"
                    st.markdown(
                        f"<div style='text-align:center; padding:10px;'>"
                        f"<div style='font-size:32px; font-weight:800; color:{score_color};'>{score:.0f}%</div>"
                        f"<div style='font-size:12px; color:#888;'>Match Score</div></div>",
                        unsafe_allow_html=True,
                    )

                if job.get("match_reasoning"):
                    st.markdown("**AI Analysis:**")
                    st.info(job["match_reasoning"])

                if job.get("description"):
                    with st.expander("📄 Full Description"):
                        st.text(job["description"][:3000])
    else:
        st.info("No jobs found. Use the search form above to scrape jobs from multiple sources.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AI Matching
# ══════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Matching":
    st.markdown("## 🤖 AI Matching")
    st.markdown("Score all jobs against your profile using AI.")

    api_key = os.environ.get("OPENAI_API_KEY", get_setting("openai_api_key", ""))
    if not api_key:
        st.warning("⚠️ OpenAI API key required. Set it in ⚙️ Settings.")
    else:
        os.environ["OPENAI_API_KEY"] = api_key

        from core.matcher import score_unscored_jobs, rescore_job

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 Score All Unscored Jobs", type="primary", use_container_width=True):
                with st.spinner("Scoring jobs with AI... This may take a minute."):
                    scored = score_unscored_jobs(limit=50)
                st.success(f"✅ Scored {scored} jobs!")
                st.rerun()

        with col2:
            rescore_id = st.number_input("Rescore specific job ID", min_value=1, step=1)
            if st.button("🔄 Rescore", use_container_width=True):
                with st.spinner("Rescoring..."):
                    result = rescore_job(int(rescore_id))
                if result:
                    st.success(f"New score: {result['score']}%")
                    st.info(result["reasoning"])

        # Score distribution
        st.markdown("---")
        st.markdown("### 📊 Score Distribution")
        all_jobs = get_jobs(limit=500)
        scored_jobs = [j for j in all_jobs if j["match_score"] > 0]

        if scored_jobs:
            df = pd.DataFrame(scored_jobs)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Distribution**")
                bins = {"90-100 ⭐": 0, "75-89 🟢": 0, "60-74 🟡": 0, "40-59 🟠": 0, "0-39 🔴": 0}
                for j in scored_jobs:
                    s = j["match_score"]
                    if s >= 90: bins["90-100 ⭐"] += 1
                    elif s >= 75: bins["75-89 🟢"] += 1
                    elif s >= 60: bins["60-74 🟡"] += 1
                    elif s >= 40: bins["40-59 🟠"] += 1
                    else: bins["0-39 🔴"] += 1
                st.bar_chart(pd.DataFrame(list(bins.items()), columns=["Range", "Count"]).set_index("Range"))

            with col2:
                st.markdown("**Top 10 Matches**")
                for j in sorted(scored_jobs, key=lambda x: x["match_score"], reverse=True)[:10]:
                    st.markdown(f"**{j['match_score']:.0f}%** — {j['title']} @ {j['company']}")
        else:
            st.info("No scored jobs yet. Click 'Score All Unscored Jobs' to start.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Generate Materials
# ══════════════════════════════════════════════════════════════════════════
elif page == "✨ Generate Materials":
    st.markdown("## ✨ Generate Application Materials")
    st.markdown("AI-powered cover letters, resume bullets, and application emails.")

    api_key = os.environ.get("OPENAI_API_KEY", get_setting("openai_api_key", ""))
    if not api_key:
        st.warning("⚠️ OpenAI API key required. Set it in ⚙️ Settings.")
    else:
        os.environ["OPENAI_API_KEY"] = api_key

        from core.generator import generate_cover_letter, generate_resume_bullets, generate_application_email, generate_and_save

        # Select job
        all_jobs = get_jobs(min_score=40, limit=50)
        if not all_jobs:
            all_jobs = get_jobs(limit=50)

        if all_jobs:
            job_options = {
                f"{j['title']} @ {j['company']} [{j['match_score']:.0f}%]": j["id"]
                for j in all_jobs
            }
            selected_job = st.selectbox("Select a job", list(job_options.keys()))
            job_id = job_options[selected_job]

            col1, col2, col3 = st.columns(3)

            with col1:
                style = st.selectbox("Style", ["professional", "academic", "startup"])

            with col2:
                gen_type = st.selectbox("Generate", ["Cover Letter", "Resume Bullets", "Application Email", "All (Save as Application)"])

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                generate_btn = st.button("✨ Generate", type="primary", use_container_width=True)

            if generate_btn:
                with st.spinner("AI is crafting your materials..."):
                    try:
                        if gen_type == "Cover Letter":
                            result = generate_cover_letter(job_id, style=style)
                            st.markdown("### 📝 Cover Letter")
                            st.text_area("", value=result, height=400, key="cl_output")
                            st.download_button("📥 Download", result, file_name="cover_letter.txt")

                        elif gen_type == "Resume Bullets":
                            result = generate_resume_bullets(job_id)
                            st.markdown("### 📋 Resume Optimization")
                            st.markdown(result)

                        elif gen_type == "Application Email":
                            result = generate_application_email(job_id)
                            st.markdown("### ✉️ Application Email")
                            st.text_area("", value=result, height=300, key="email_output")
                            st.download_button("📥 Download", result, file_name="application_email.txt")

                        elif gen_type == "All (Save as Application)":
                            app_id = generate_and_save(job_id, style=style)
                            st.success(f"✅ Application #{app_id} created! View it in 📝 Applications.")

                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("No jobs in database. Scrape some jobs first in 🔍 Job Discovery.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Applications
# ══════════════════════════════════════════════════════════════════════════
elif page == "📝 Applications":
    st.markdown("## 📝 Applications")
    st.markdown("Track and manage your applications.")

    from core.auto_apply import prepare_application, detect_ats
    from core.matcher import load_profile

    apps = get_applications()

    if apps:
        for app in apps:
            with st.expander(
                f"{'✅' if app['status'] == 'applied' else '📝' if app['status'] == 'draft' else '🔄'} "
                f"**{app['title']}** — {app['company']} [{app['match_score']:.0f}%]"
            ):
                col1, col2 = st.columns([3, 1])

                with col1:
                    if app.get("cover_letter"):
                        st.markdown("**Cover Letter:**")
                        st.text_area("", value=app["cover_letter"], height=200, key=f"cl_{app['id']}")

                    if app.get("url"):
                        ats = detect_ats(app["url"])
                        st.markdown(f"**ATS:** {ats or 'Unknown'}")
                        st.markdown(f"[🔗 Apply Now]({app['url']})")

                with col2:
                    from core.database import update_application
                    new_status = st.selectbox(
                        "Status",
                        ["draft", "applied", "interviewing", "offer", "rejected"],
                        index=["draft", "applied", "interviewing", "offer", "rejected"].index(app.get("status", "draft")),
                        key=f"app_status_{app['id']}",
                    )
                    if new_status != app.get("status"):
                        update_application(app["id"], status=new_status)
                        if new_status == "applied":
                            update_application(app["id"], applied_at=datetime.now().isoformat())
                        st.rerun()

                    st.markdown(f"**Created:** {app.get('created_at', 'N/A')[:10]}")
                    if app.get("applied_at"):
                        st.markdown(f"**Applied:** {app['applied_at'][:10]}")
    else:
        st.info("No applications yet. Generate materials in ✨ Generate Materials to create your first application.")

    # Quick apply section
    st.markdown("---")
    st.markdown("### ⚡ Quick Apply")
    st.markdown("Select high-scoring jobs to prepare applications in bulk.")

    top_jobs = get_jobs(min_score=60, limit=20)
    if top_jobs:
        selected_ids = []
        for job in top_jobs:
            if st.checkbox(
                f"{job['title']} @ {job['company']} — {job['match_score']:.0f}%",
                key=f"quick_{job['id']}",
            ):
                selected_ids.append(job["id"])

        if selected_ids and st.button(f"✨ Prepare {len(selected_ids)} Applications", type="primary"):
            profile = load_profile()
            with st.spinner("Preparing applications..."):
                from core.auto_apply import batch_prepare
                results = batch_prepare(selected_ids, profile)

            for result in results:
                if "error" not in result:
                    st.success(f"✅ {result['job_title']} @ {result['company']} — Method: {result['method']}")
                else:
                    st.error(f"❌ Job {result.get('job_id')}: {result['error']}")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Settings
# ══════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")

    # API Keys
    st.markdown("### 🔑 API Keys")

    with st.form("api_keys_form"):
        openai_key = st.text_input(
            "OpenAI API Key",
            value=get_setting("openai_api_key", ""),
            type="password",
            help="Required for AI matching and material generation. Get one at platform.openai.com",
        )
        serpapi_key = st.text_input(
            "SerpAPI Key",
            value=get_setting("serpapi_key", ""),
            type="password",
            help="For Google Jobs scraping. Free 100 searches/month at serpapi.com",
        )
        adzuna_id = st.text_input(
            "Adzuna App ID",
            value=get_setting("adzuna_app_id", ""),
            help="Free at developer.adzuna.com",
        )
        adzuna_key = st.text_input(
            "Adzuna App Key",
            value=get_setting("adzuna_app_key", ""),
            type="password",
        )
        usajobs_key = st.text_input(
            "USAJobs API Key",
            value=get_setting("usajobs_api_key", ""),
            type="password",
            help="Free at developer.usajobs.gov",
        )
        usajobs_email = st.text_input(
            "USAJobs Email",
            value=get_setting("usajobs_email", ""),
        )

        if st.form_submit_button("💾 Save API Keys", type="primary"):
            set_setting("openai_api_key", openai_key)
            set_setting("serpapi_key", serpapi_key)
            set_setting("adzuna_app_id", adzuna_id)
            set_setting("adzuna_app_key", adzuna_key)
            set_setting("usajobs_api_key", usajobs_key)
            set_setting("usajobs_email", usajobs_email)

            # Also set env vars
            os.environ["OPENAI_API_KEY"] = openai_key
            os.environ["SERPAPI_KEY"] = serpapi_key
            os.environ["ADZUNA_APP_ID"] = adzuna_id
            os.environ["ADZUNA_APP_KEY"] = adzuna_key
            os.environ["USAJOBS_API_KEY"] = usajobs_key
            os.environ["USAJOBS_EMAIL"] = usajobs_email

            st.success("✅ API keys saved!")

    # Email settings
    st.markdown("### ✉️ Email Settings (for auto-apply)")
    with st.form("email_form"):
        smtp_server = st.text_input("SMTP Server", value=get_setting("smtp_server", "smtp.gmail.com"))
        smtp_port = st.number_input("SMTP Port", value=int(get_setting("smtp_port", "587")))
        smtp_user = st.text_input("Email Address", value=get_setting("smtp_user", ""))
        smtp_pass = st.text_input("App Password", value=get_setting("smtp_pass", ""), type="password",
                                  help="For Gmail: use an App Password, not your account password")

        if st.form_submit_button("💾 Save Email Settings"):
            set_setting("smtp_server", smtp_server)
            set_setting("smtp_port", str(smtp_port))
            set_setting("smtp_user", smtp_user)
            set_setting("smtp_pass", smtp_pass)
            st.success("✅ Email settings saved!")

    # Profile
    st.markdown("### 👤 Profile")
    profile_path = os.environ.get("PROFILE_PATH", "data/profile.json")
    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile_data = f.read()

        edited_profile = st.text_area("Profile JSON", value=profile_data, height=400)
        if st.button("💾 Save Profile"):
            try:
                json.loads(edited_profile)  # Validate JSON
                with open(profile_path, "w") as f:
                    f.write(edited_profile)
                st.success("✅ Profile saved!")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
    else:
        st.warning("No profile found. Create data/profile.json with your information.")

    # Danger zone
    st.markdown("### ⚠️ Danger Zone")
    if st.button("🗑️ Reset Database", type="secondary"):
        if st.checkbox("I understand this will delete all jobs and applications"):
            os.remove("data/jobs.db") if os.path.exists("data/jobs.db") else None
            init_db()
            st.success("Database reset!")
            st.rerun()
