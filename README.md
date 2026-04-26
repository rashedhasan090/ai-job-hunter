# 🎯 AI Job Hunter

An AI-powered job search autopilot that scrapes jobs from multiple sources, matches them to your profile, generates tailored application materials, and helps you apply at scale.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?logo=streamlit)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green?logo=openai)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 🔍 Multi-Source Job Scraping
- **Google Jobs** (via SerpAPI) — most comprehensive search engine
- **Adzuna** — structured job data with salary info
- **Remotive** — remote tech jobs (no API key needed)
- **Arbeitnow** — remote/hybrid positions (no API key needed)
- **USAJobs** — government positions
- **HigherEdJobs** — academic/faculty positions

### 🤖 AI-Powered Matching
- Scores every job against your profile (0-100)
- Explains *why* each job matches or doesn't
- Flags visa/sponsorship concerns
- Suggests application strategy per job
- Highlights skill gaps and matching qualifications

### ✨ Material Generation
- **Tailored cover letters** — professional, academic, or startup style
- **Resume optimization** — suggests which experiences to emphasize
- **Application emails** — for positions accepting email applications
- **One-click generation** — save everything as a tracked application

### 📝 Application Tracking
- Full pipeline: Draft → Applied → Interviewing → Offer
- ATS detection (Lever, Greenhouse, Workday, etc.)
- Pre-fill data for quick portal completion
- Application history and notes

### ⚡ Auto-Apply
- Email-based academic applications
- Pre-filled form data for portal submissions
- ATS-aware application preparation
- Bulk application preparation for top matches

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rashedhasan090/ai-job-hunter.git
cd ai-job-hunter
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Minimum required:** OpenAI API key (`OPENAI_API_KEY`)

**Optional but recommended:**
- SerpAPI key — for Google Jobs scraping ([get free key](https://serpapi.com))
- Adzuna credentials — for structured job data ([register free](https://developer.adzuna.com))

### 3. Edit Your Profile

Edit `data/profile.json` with your information. The profile includes:
- Personal info, education, target roles
- Skills, research areas, experience
- Visa status, location preferences
- Detailed background for AI matching

### 4. Launch

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## 🌐 Deploy to Streamlit Cloud (Free)

1. Push this repo to your GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repo and `app.py` as the main file
5. Add your API keys in **Settings → Secrets**:
   ```toml
   OPENAI_API_KEY = "sk-your-key-here"
   SERPAPI_KEY = "your-key-here"
   ```
6. Click **Deploy** — your app will be live at `https://your-app.streamlit.app`

## 📁 Project Structure

```
ai-job-hunter/
├── app.py                  # Main Streamlit dashboard (all pages)
├── core/
│   ├── database.py         # SQLite storage layer
│   ├── scraper.py          # Multi-source job scraper
│   ├── matcher.py          # AI-powered job matching
│   ├── generator.py        # Cover letter / resume generator
│   └── auto_apply.py       # Auto-apply engine
├── data/
│   ├── profile.json        # Your profile (edit this!)
│   └── jobs.db             # SQLite database (auto-created)
├── .streamlit/
│   └── config.toml         # Streamlit theme configuration
├── .env.example            # API keys template
├── requirements.txt        # Python dependencies
├── Procfile                # For Render/Railway deployment
└── README.md
```

## 🔧 Configuration

### API Keys

| API | Purpose | Free Tier | Link |
|-----|---------|-----------|------|
| OpenAI | AI matching & generation | Pay-per-use (~$0.01/job) | [platform.openai.com](https://platform.openai.com) |
| SerpAPI | Google Jobs scraping | 100 searches/month | [serpapi.com](https://serpapi.com) |
| Adzuna | Structured job data | 400 calls/month | [developer.adzuna.com](https://developer.adzuna.com) |
| USAJobs | Government jobs | Unlimited (free) | [developer.usajobs.gov](https://developer.usajobs.gov) |

### Profile Customization

Edit `data/profile.json` to match your background. Key fields:

- `target_roles` — job titles you're looking for
- `research_areas` — your research expertise
- `skills` — technical skills
- `visa_status` — for sponsorship flagging
- `detailed_background` — awards, teaching, publications

## 📊 Workflow

```
1. Configure      →  Set API keys + edit profile
2. Discover       →  Scrape jobs from multiple sources
3. Match          →  AI scores every job (0-100)
4. Generate       →  Create tailored materials for top matches
5. Apply          →  One-click apply or tracked manual submission
6. Track          →  Monitor application pipeline
```

## 🛡️ Privacy & Security

- All data stays local (SQLite database)
- API keys stored in `.env` (gitignored) or Streamlit Secrets
- No data shared with third parties beyond API calls
- Profile data never leaves your machine except for AI scoring

## 🤝 Contributing

PRs welcome! Areas for improvement:
- Additional job board scrapers
- Browser extension for auto-fill
- LinkedIn Easy Apply integration
- Interview scheduling integration
- Analytics and reporting

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with ❤️ by [Viktor AI](https://getviktor.com) for Md Rashedul Hasan
