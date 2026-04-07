# ads.txt Monitor

Checks 10 ads.txt / app-ads.txt files daily, writes a diff to an Excel workbook,
and emails you a colour-coded summary with the workbook attached.

Runs on **GitHub Actions** — free, no server required.

---

## Setup (5 minutes)

### 1. Create a new GitHub repo

Create a **private** repo (keeps your snapshots private) and push these files into it.

```
adstxt-monitor/
├── .github/workflows/monitor.yml
├── monitor.py
├── requirements.txt
└── README.md
```

### 2. Create a Gmail App Password

Your monitor sends email through Gmail using an App Password (not your regular password).

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already on
3. Search for **"App Passwords"** → create one named "adstxt monitor"
4. Copy the 16-character password — you won't see it again

> **Note:** App Passwords only appear if 2-Step Verification is enabled.

### 3. Add GitHub Secrets

In your repo go to **Settings → Secrets and variables → Actions → New repository secret**
and add these three secrets:

| Secret name         | Value                                      |
|---------------------|--------------------------------------------|
| `GMAIL_USER`        | your Gmail address, e.g. `you@gmail.com`   |
| `GMAIL_APP_PASSWORD`| the 16-char App Password from step 2       |
| `NOTIFY_EMAIL`      | email address to send reports to           |

> `GMAIL_USER` and `NOTIFY_EMAIL` can be the same address if you want to send to yourself.

### 4. Grant Actions write permission

The workflow commits `snapshots.json` and `adstxt_changes.xlsx` back to the repo after each run.

Go to **Settings → Actions → General → Workflow permissions** and select
**"Read and write permissions"**, then save.

### 5. Run it for the first time

Go to **Actions → ads.txt Monitor → Run workflow**.

This creates the first snapshot (no diffs yet — nothing to compare against).
From the second run onwards you'll receive change emails.

---

## Schedule

Runs at **9:00 AM UTC (5:00 AM ET)** every day.
To change the time, edit the `cron:` line in `.github/workflows/monitor.yml`.

```yaml
# Examples
- cron: "0 9 * * *"      # 9 AM UTC daily (current)
- cron: "0 13 * * 1-5"   # 1 PM UTC weekdays only
- cron: "0 */6 * * *"    # every 6 hours
```

---

## What you get

### Email
- Colour-coded table: **Changed** (red), **OK** (grey), **Error** (yellow), **New** (blue)
- Expandable sections showing added / removed lines for each changed file
- Excel workbook attached

### Excel workbook (`adstxt_changes.xlsx`)
| Sheet | Contents |
|-------|----------|
| **Change Log** | Every daily run — timestamp, file, status, line counts, diff preview |
| **Current Snapshot** | Latest status of all 10 files |
| **`domain_ads_txt`** | Per-file diff sheet (only created when a file changes) |

The workbook is also committed to the repo after every run, so you have a full history in git.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Email not arriving | Check spam; verify App Password is correct |
| `403 Forbidden` on a URL | The site may block bots — the error is logged and won't crash the run |
| `push` fails in Actions | Make sure Workflow permissions are set to read/write (step 4) |
| Want to reset all snapshots | Delete `snapshots.json` from the repo and re-run |
