# OpenClaw Integration — Setup & Usage Guide

> Automated daily LLM evaluations → graphs → Telegram approval → LinkedIn + Twitter posting.

## Architecture

```
┌─ Railway Project ──────────────────────────────────────────┐
│                                                            │
│  ┌─ backend service ────┐   ┌─ openclaw service ──────────┐│
│  │  FastAPI :8000        │←──│  OpenClaw gateway           ││
│  │  Galileo eval engine  │   │  Cron: daily 08:00 CET      ││
│  │  Supabase DB          │   │  Skills: daily-eval-report   ││
│  └───────────────────────┘   └─────────────────────────────┘│
│        ↑ private network                                    │
│   backend.railway.internal:8000                             │
│                                                             │
│   External connections:                                     │
│    → Telegram Bot API (approval messages)                   │
│    → DeepSeek API (LLM reasoning + AI content)              │
│    → LinkedIn Posts API (publish with images)                │
│    → Twitter/X API via bird skill (tweet threads)            │
└─────────────────────────────────────────────────────────────┘
```

## Daily Workflow

1. **08:00 CET** — OpenClaw cron fires
2. **Run evals** — `run_eval_report.py` runs 6 LLMs × 2 datasets × 2 cases
3. **Fetch 7-day data** — pulls 7-day summary + trend from Galileo API
4. **Generate content** — charts, branded infographics, cover art, bar race video, AI-written posts (themed by day-of-week)
5. **Send to Telegram** — you see the drafts + graphs + AI commentary in your Telegram chat
6. **You reply** — pick LinkedIn option, Twitter thread, which images to use
7. **On approval** — posts to LinkedIn (API) and Twitter (bird skill)

---

## Prerequisites

| What | Why |
|------|-----|
| Node.js ≥ 22 | OpenClaw gateway runtime |
| Python ≥ 3.12 | Eval scripts, AI content generation |
| DeepSeek API key | Powers OpenClaw's AI reasoning + content |
| Telegram bot token | Sends you drafts for approval |
| LinkedIn developer app | OAuth token for API posting |
| Twitter API keys | bird skill posts tweet threads |

> [!TIP]
> You need at least **1 GB RAM** (4 GB recommended). On a VPS with < 2 GB RAM, create a 4 GB swap file.

---

## Step 1: Install OpenClaw

### 1.1 Run the installer

**Windows (PowerShell as Admin):**
```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

**Windows (PowerShell as Admin): if need to unistall preexisting**
```powershell
npm uninstall -g openclaw

Remove-Item -Recurse -Force "$env:USERPROFILE\.openclaw"

```

**macOS / Linux / WSL2:**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash

```

**Or via npm (if Node.js 22+ is already installed):**
```bash
npm install -g openclaw@latest
```

### 1.2 Run the onboarding wizard

The installer launches this automatically. If it doesn't:

```bash
openclaw onboard
```

The wizard will ask you to:

1. **Choose mode** → select **Quick Start**
2. **Choose AI provider** → select **OpenAI-Compatible** and enter:
   - API Base: `https://api.deepseek.com/v1`
   - API Key: your `DEEPSEEK_API_KEY`
3. **Connect messaging platform** → select **Telegram**
   - Go to Telegram → [@BotFather](https://t.me/BotFather) → `/newbot`
   - Give it a name (e.g., "Galileo Arena Bot")
   - Copy the bot token → paste into wizard
4. **Install daemon** → select **Yes** (keeps gateway running)

### 1.3 Verify installation

```bash
openclaw gateway status     # should show "running"
openclaw dashboard          # opens Control UI at http://127.0.0.1:18789
```

### 1.4 Pair with Telegram
if The gateway isn't running 

```bash
openclaw gateway run
```

Then in a **new terminal**, symlink the custom skill into the OpenClaw workspace:

**Windows (PowerShell):**
```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.openclaw\workspace\skills\daily-eval-report" -Target "s:\SYNC\programming\AIGalileoArena\openclaw\skills\daily-eval-report"
```

**macOS / Linux:**
```bash
ln -s /path/to/AIGalileoArena/openclaw/skills/daily-eval-report ~/.openclaw/workspace/skills/daily-eval-report
```



After the gateway starts, check the logs or run:

```bash
openclaw pairing list telegram
openclaw pairing approve telegram <CODE>
```

Then **send your bot a message on Telegram** (e.g., "hello"). It should reply — you're connected.

### 1.5 Register the project skills

Custom skills live in `~/.openclaw/workspace/skills/`. Create a symlink to keep it in sync with your repo:

**Windows (PowerShell):**
```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.openclaw\workspace\skills\daily-eval-report" `
  -Target "s:\SYNC\programming\AIGalileoArena\openclaw\skills\daily-eval-report"
```

**macOS / Linux:**
```bash
ln -s /path/to/AIGalileoArena/openclaw/skills/daily-eval-report \
  ~/.openclaw/workspace/skills/daily-eval-report
```

Verify it's detected:

```bash
openclaw skills list
# Should show: daily-eval-report
```

### 1.6 Register the daily cron job

```bash
openclaw cron add \
  --name "Daily LLM Eval Report" \
  --cron "0 8 * * *" \
  --tz "Europe/Amsterdam" \
  --session isolated \
  --message "Run /daily-eval-report" \
  --no-deliver
```

Verify:

```bash
openclaw cron list
# Should show the job with next fire time
```

> [!NOTE]
> The `start.sh` entrypoint auto-registers this cron on Railway deploy.
> The manual steps above are for **local development** only.

---

## Step 2: DeepSeek API Key

1. Go to [platform.deepseek.com](https://platform.deepseek.com)
2. Create account → API Keys → **Create new key**
3. Copy the key
4. Add to `openclaw/.env`:
   ```
   DEEPSEEK_API_KEY=sk-...
   ```

---

## Step 3: Telegram Bot

> Already done during onboarding (Step 1.2). If you need to create a new bot:

1. Open Telegram → search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts — give it a name (e.g., "Galileo Arena Bot")
4. BotFather gives you a **bot token** — copy it
5. Save as `TELEGRAM_BOT_TOKEN` in Railway

### First-time pairing

After deploying, check OpenClaw logs for the pairing code, then approve:


```bash
openclaw pairing list telegram
openclaw pairing approve telegram <CODE>
```

Then send your bot a message on Telegram. It's now connected.

---

## Step 4: LinkedIn API

### 4.1 Create Developer App

1. Go to [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
2. **Create App** → fill in app name, company page, logo
3. **Products** tab → request **Share on LinkedIn** (grants `w_member_social`)
4. **Auth** tab → copy **Client ID** and **Client Secret**
5. Add redirect URL: `http://localhost:9876/callback`

### 4.2 Get Access Token (one-time, local)

```bash
cd openclaw
python scripts/linkedin_auth.py \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

This opens a browser for LinkedIn OAuth consent, captures the callback, and prints:
- **Access token** (valid 60 days)
- **Person URN** (`urn:li:person:XXXXXXX`)

### 4.3 Save as Railway env vars

```
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_PERSON_URN=urn:li:person:XXXXXXX
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
```

> ⚠️ **Token expires after 60 days.** Re-run `linkedin_auth.py` to refresh.

---

## Step 5: Twitter/X API

1. Go to [developer.x.com](https://developer.x.com)
2. Create a project + app
3. Generate **API Key**, **API Secret**, **Access Token**, **Access Secret**
4. Set as Railway env vars:

```
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
```

---

## Step 6: Deploy to Railway

### Add the service

1. Railway dashboard → your project → **New Service**
2. Source: **GitHub Repo** (same repo)
3. **Root Directory**: `openclaw`
4. Railway auto-detects the `Dockerfile`

### Environment variables

| Variable | Value |
|----------|-------|
| `DEPLOY_ENV` | `production` |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `LINKEDIN_ACCESS_TOKEN` | From step 4.2 |
| `LINKEDIN_PERSON_URN` | `urn:li:person:XXXXX` |
| `LINKEDIN_CLIENT_ID` | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn app client secret |
| `TWITTER_API_KEY` | Twitter API key |
| `TWITTER_API_SECRET` | Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | Twitter access token |
| `TWITTER_ACCESS_SECRET` | Twitter access secret |
| `BACKEND_URL` | `http://backend.railway.internal:8000` |

### Cron registration

The `start.sh` entrypoint auto-registers the cron job on first boot. If you need to re-register manually:

```bash
openclaw cron add \
  --name "Daily LLM Eval Report" \
  --cron "0 8 * * *" \
  --tz "Europe/Amsterdam" \
  --session isolated \
  --message "Run /daily-eval-report" \
  --no-deliver
```

---

## Usage

### Automatic (daily at 08:00)

The cron fires → evals run → you get a **Telegram message** with:
- 🔍 AI-generated insights/commentary
- 📊 Leaderboard infographic + trend chart + cover art
- 🎬 Bar race video (MP4)
- 📝 3 LinkedIn post options (AI-written, themed by day)
- 🐦 Narrative Twitter thread draft

Reply in Telegram:
- "LinkedIn 2 with the infographic" → publishes option 2 with image
- "Twitter 1" → posts the thread
- Or give edit instructions: "Make option 1 shorter and add a Dutch version"

### Manual trigger

```bash
openclaw cron list          # see job IDs
openclaw cron run <job-id>  # trigger now
```

### Test locally

```bash
$env:DEEPSEEK_API_KEY = (Get-Content .env | Select-String "^DEEPSEEK_API_KEY=" | ForEach-Object { $_.Line.Split("=", 2)[1] })

python scripts/run_eval_report.py --base http://localhost:8000 --skip-eval
python scripts/run_eval_report.py --skip-eval --force-theme 4  # Friday spotlight
```

---

## Dev vs Prod LinkedIn Posting

LinkedIn posting mode is controlled by the `DEPLOY_ENV` environment variable:

| `DEPLOY_ENV` | Method | Requirements |
|--------------|--------|--------------|
| `production` | LinkedIn REST API | `LINKEDIN_ACCESS_TOKEN` + `LINKEDIN_PERSON_URN` |
| `development` (default) | Playwright browser automation | Log in once via browser |

### Local dev setup

1. Install Playwright:
   ```bash
   pip install playwright>=1.49.0
   playwright install chromium
   ```

2. Set `DEPLOY_ENV=development` in `openclaw/.env` (this is the default).

3. Run the posting script — a Chromium window opens on first run:
   ```bash
   python scripts/linkedin_post.py --text "Test post from dev"
   ```

4. Log in to LinkedIn in the browser. Your session is saved to `scripts/.linkedin_profile/`.

5. Subsequent runs are **headless** — no browser window needed.

> [!TIP]
> To force a visible browser (e.g. if session expired), set `LINKEDIN_BROWSER_HEADLESS=false`.

---

## File Structure

```
openclaw/
├── Dockerfile                  # Node.js 22.14 + Python 3.12 + ffmpeg
├── requirements.txt            # httpx, matplotlib, Pillow, qrcode (pinned)
├── scripts/
│   ├── start.sh                # Entrypoint: config gen + gateway
│   ├── generate_config.py      # Secure runtime config (no templates)
│   ├── run_eval_report.py      # Orchestrator + content calendar
│   ├── ai_writer.py            # DeepSeek AI content generation
│   ├── infographic.py          # Pillow branded graphics + cover art
│   ├── video_charts.py         # Bar chart race video (MP4)
│   ├── engagement.py           # Post performance tracking
│   ├── brand_config.py         # Colors, fonts, layout, themes
│   ├── linkedin_auth.py        # One-time OAuth token flow
│   ├── linkedin_post.py        # Post to LinkedIn (dispatcher: API or browser)
│   └── linkedin_post_browser.py # Browser automation posting (Playwright)
├── skills/
│   └── daily-eval-report/
│       └── SKILL.md            # OpenClaw skill definition
└── reports/                    # Generated daily (YYYY-MM-DD/)
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| LinkedIn token expired | Re-run `linkedin_auth.py` locally, update Railway env var |
| Telegram bot not responding | Check gateway logs, verify bot token, ensure bot was messaged once |
| Evals failing | Check backend is reachable at `BACKEND_URL` |
| Tweets over 280 chars | Script auto-truncates, but check `twitter_thread.txt` |
| Cron not firing | Verify with `openclaw cron list`, check timezone |
| AI content empty | Check `DEEPSEEK_API_KEY` and rate cap in logs |
| Video generation slow | On Railway CPU, expect ~20-30s. Can reduce FPS in `video_charts.py` |

# to save lindin credentials
python scripts/linkedin_post.py --text "test"
