# 🌍 Real-Time Geospatial Alerting Agent

> **Production-grade automated pipeline that polls live USGS earthquake data, performs spatial joins against infrastructure assets, and sends real-time email alerts.**

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue?logo=githubactions)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://python.org)
[![USGS API](https://img.shields.io/badge/Data%20Source-USGS%20Earthquake%20API-green)](https://earthquake.usgs.gov/fdsnws/event/1/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 What This Project Does

This agent solves a real-world operations problem: **How do you know if your facilities are near a natural disaster as soon as it happens?**

1. **Extract** — Polls the live USGS Earthquake API every hour (no API key required).
2. **Transform** — Performs a **spatial join** using the Haversine formula to calculate exact distances between earthquake epicenters and your asset locations.
3. **Load / Alert** — Automatically sends formatted HTML email alerts when an earthquake falls within a user-defined buffer radius.
4. **Audit** — Saves timestamped JSON logs of every run for compliance and debugging.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   USGS API      │────▶│  Spatial Join    │────▶│  Email Alerts   │
│ (Free, Live)    │     │ (Haversine/      │     │ (SMTP/Gmail)    │
│                 │     │  Point-in-Buffer)│     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         ▲                                               │
         │                                               │
    ┌────┴────┐                                   ┌──────┴──────┐
    │ GitHub  │                                   │  JSON Logs  │
    │ Actions │                                   │  (Audit)    │
    │(Cron)   │                                   │             │
    └─────────┘                                   └─────────────┘
```

---

## 🗂️ Project Structure

```
geospatial-alert-agent/
├── .github/
│   └── workflows/
│       └── alert.yml          # CI/CD automation (runs every hour)
├── data/
│   └── assets.csv             # Your facilities & buffer zones
├── src/
│   └── alert_agent.py         # Core pipeline script
├── logs/                      # Auto-generated audit logs
├── .env.example               # Template for local secrets
├── requirements.txt           # Python dependencies
└── README.md                  # You are here
```

---

## 🚀 Quick Start (Local — VS Code)

### 1. Install Prerequisites (Free)
- **VS Code** → [Download](https://code.visualstudio.com/)
- **Python 3.14** → [Download](https://www.python.org/downloads/)
- **Git** → [Download](https://git-scm.com/downloads)

### 2. Clone / Open the Project
Open the folder in VS Code:
```bash
# If you cloned from GitHub:
cd geospatial-alert-agent
```

### 3. Create a Virtual Environment (Recommended)
In VS Code, open the terminal (`Ctrl + ~`) and run:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
```bash
# Copy the template
cp .env.example .env        # Mac/Linux
copy .env.example .env      # Windows
```

Edit `.env` and add your Gmail credentials:
```ini
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
TEST_MODE=true   # <-- Set to true first to test safely
```

> **How to get a Gmail App Password:**
> 1. Enable 2-Factor Auth: https://myaccount.google.com/signinoptions/two-step-verification
> 2. Generate App Password: https://myaccount.google.com/apppasswords
> 3. Select "Mail" → "Other (Custom name)" → Type "GeoAlert" → Copy the 16-char password.

### 6. Run the Agent
```bash
python src/alert_agent.py
```

You should see output like:
```
============================================================
🌍 REAL-TIME GEOSPATIAL ALERTING AGENT
============================================================

📡 STEP 1: Fetching live earthquake data from USGS...
   ✔ Retrieved 47 earthquake(s) in last 24h (mag ≥ 3.0)

🏭 STEP 2: Loading asset inventory...
   ✔ Loaded 5 asset(s) from assets.csv

🔍 STEP 3: Performing spatial join (distance analysis)...
   ✔ 2 asset(s) are within threat range!

📧 STEP 4: Sending alert notifications...
   🧪 [TEST] Would email you@gmail.com about 3 quake(s) near San Francisco HQ

📊 STEP 5: Saving audit log...
   💾 Log saved: alert_run_20240502_083000.json
```

### 7. Enable Real Emails
Once you see it working in `TEST_MODE`, edit `.env`:
```ini
TEST_MODE=false
```
Run again — check your inbox!

---

## ☁️ Deploy to GitHub Actions (Cloud Automation)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit: Geospatial Alert Agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/geospatial-alert-agent.git
git push -u origin main
```

### 2. Add Repository Secrets
Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name      | Value Example                          |
|------------------|----------------------------------------|
| `EMAIL_USERNAME` | `your-email@gmail.com`                 |
| `EMAIL_PASSWORD` | `abcd efgh ijkl mnop` (app password)   |
| `SMTP_SERVER`    | `smtp.gmail.com`                       |
| `SMTP_PORT`      | `587`                                  |
| `TEST_MODE`      | `false`                                |

### 3. Verify It Works
- Go to **Actions** tab in your repo.
- You should see the workflow.
- Click **Run workflow** → **Run workflow** (manual trigger).
- Green checkmark = success! 🎉

### 4. Let It Run Automatically
The cron schedule (`0 * * * *`) means GitHub will run this **every hour, completely free**, as long as your repo is public.

> **Free Tier Limits:** Public repos get unlimited GitHub Actions minutes. Private repos get 2,000 minutes/month — more than enough for this agent.

---

## 📊 Sample Output

### Console Output
```
✅ AGENT RUN COMPLETE
   Earthquakes checked : 47
   Assets monitored    : 5
   Assets at risk      : 2
   Alerts sent         : 2
```

### Email Alert (HTML)
<img src="https://i.imgur.com/email_mockup.png" alt="Email Alert Mockup" width="500">

*(Your actual email will contain a formatted table with magnitude, location, distance, and USGS details link.)*

### Audit Log (JSON)
```json
{
  "run_timestamp_utc": "2024-05-02T08:30:00",
  "total_earthquakes_checked": 47,
  "assets_at_risk": 2,
  "alerts": [
    {
      "asset": { "name": "San Francisco HQ", "lat": 37.7749, "lon": -122.4194, "buffer_km": 200 },
      "earthquakes": [
        { "magnitude": 4.5, "place": "10km NE of Pacifica, CA", "distance_km": 18.4, "alert_level": "MODERATE" }
      ]
    }
  ]
}
```

---

## 🛠️ Customization

### Change Assets
Edit `data/assets.csv`:
```csv
name,latitude,longitude,buffer_km,email
My House,40.7128,-74.0060,100,myemail@gmail.com
```

### Change Check Frequency
Edit `.github/workflows/alert.yml`:
```yaml
# Every 15 minutes (power user!)
- cron: '*/15 * * * *'

# Once per day at 9 AM UTC
- cron: '0 9 * * *'
```

### Switch to NWS Weather Alerts
Replace the `fetch_earthquakes()` function with calls to:
- `https://api.weather.gov/alerts/active`
- Parse polygons instead of points for true spatial intersection.

---

## 💼 How to List This on Your Resume

### Job Title Suggestions
- **Geospatial Automation Engineer**
- **GIS Data Pipeline Developer**
- **Geospatial DevOps Specialist**

### Resume Bullet Points
> - **Built a production geospatial alerting pipeline** using Python, USGS APIs, and GitHub Actions CI/CD, performing real-time spatial joins to monitor infrastructure risk across 5+ global assets.
> - **Automated ETL and notification systems** that poll live disaster APIs every hour, calculate Haversine distances, and trigger SMTP email alerts when threats enter user-defined buffer zones.
> - **Implemented full audit logging** in JSON format for compliance tracking, with artifacts stored via GitHub Actions for 7-day retention and post-run analysis.
> - **Technologies:** Python, GitHub Actions, REST APIs, SMTP, Spatial Analysis, Haversine Formula, CSV/JSON ETL, Environment Security (Secrets Management)

### Portfolio Presentation
1. **GitHub Repo** → Link to this repo (employers love seeing green checkmarks in the Actions tab).
2. **Screenshots** → Capture the Actions tab, a received email, and a JSON log.
3. **Blog Post** → Write a 5-minute read on Medium/LinkedIn:
   - *"How I Built a Real-Time Earthquake Alert System for Free"*

---

## 🧠 Skills Demonstrated

| Category              | Skills                                                        |
|-----------------------|---------------------------------------------------------------|
| **Geospatial**        | Spatial joins, buffer analysis, coordinate systems, Haversine |
| **Data Engineering**  | ETL pipelines, REST API polling, JSON/CSV processing          |
| **Automation**        | Cron scheduling, CI/CD, GitHub Actions, event-driven architecture |
| **Software Dev**      | Python, environment management, modular code, error handling  |
| **DevOps / Security** | Secret management, SMTP configuration, audit logging          |

---

## 📜 License

MIT — Free to use, modify, and showcase in your portfolio.

---

## 🙋 Need Help?

If you get stuck:
1. Check the **logs/** folder for error details.
2. Set `TEST_MODE=true` to debug without sending emails.
3. Verify your Gmail App Password (not your regular password).
4. Open an Issue on GitHub — include your log file.

**Built with 💙 by Gowshik P — Geospatial Engineer**
