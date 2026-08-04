---
name: daily-eval-report
description: Run AI Galileo Arena LLM evaluations, generate graphs, and post results to LinkedIn + Twitter after Discord approval
---

# Daily LLM Eval Report

Runs the AI Galileo Arena evaluation suite against 6 LLMs, fetches 7-day historical performance data, generates graphs, and creates social media posts for LinkedIn and Twitter/X.

## Full Workflow

### Step 1: Run the evaluation and generate reports

Execute the eval report script using the `exec` tool:

```
cd s:/SYNC/programming/AIGalileoArena/backend && .venv/Scripts/python.exe scripts/run_eval_report.py --base http://localhost:8000
```

This produces a dated folder under `s:/SYNC/programming/AIGalileoArena/backend/reports/YYYY-MM-DD/` containing:
- `leaderboard.png` — 7-day leaderboard bar chart
- `trend.png` — 7-day daily score trend lines
- `linkedin_option_1.txt` — LinkedIn post option 1 (data-driven)
- `linkedin_option_2.txt` — LinkedIn post option 2 (storytelling)
- `linkedin_option_3.txt` — LinkedIn post option 3 (visual/minimal)
- `twitter_thread.txt` — 3-4 tweet thread (each ≤280 chars)
- `summary.json` — raw ranked data

### Step 2: Send to Discord for approval

Use the `message` tool to send me the following on Discord:

1. The **leaderboard.png** and **trend.png** images
2. All 3 LinkedIn post options, clearly labeled as **Option 1**, **Option 2**, **Option 3**
3. The Twitter thread draft
4. Ask: **"Which LinkedIn option do you want to post? Reply `yes 1`, `yes 2`, or `yes 3`. Or tell me what to change."**

### Step 3: Wait for my approval

Wait for my response on Discord:
- **"yes 1"** / **"yes 2"** / **"yes 3"** → proceed with that LinkedIn option + the Twitter thread
- **Any other reply** → treat as edit instructions, revise the drafts, and re-send for approval

### Step 4: Post to LinkedIn

Once approved, use the **browser** tool to post the chosen LinkedIn option:

1. Open `https://www.linkedin.com/feed/` in the browser
2. Take a snapshot and click the "Start a post" button
3. Type/paste the approved LinkedIn post text into the composer
4. Attach the `leaderboard.png` image
5. Click the "Post" button
6. Confirm it posted successfully

### Step 5: Post to Twitter/X

Use the **bird** skill to post the Twitter thread:

1. Post the first tweet (Tweet 1 from `twitter_thread.txt`)
2. Reply to it with Tweet 2
3. Reply to Tweet 2 with Tweet 3
4. Continue until all tweets are posted
5. Attach `leaderboard.png` to the first tweet if possible

## Important Notes

- Each tweet MUST be ≤280 characters (Twitter free tier limit)
- The backend API must be running at the `--base` URL for evals to work
- LinkedIn requires being logged in via an OpenClaw browser profile (log in once manually)
- If the bird skill is not installed: `clawhub install bird`
- Use `--skip-eval` flag if you only want to regenerate reports from existing data
