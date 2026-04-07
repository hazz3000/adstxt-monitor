name: ads.txt Monitor

on:
  schedule:
    - cron: "0 9 * * *"   # 9:00 AM UTC daily (5 AM ET)
  workflow_dispatch:       # manual runs from the Actions tab

jobs:
  monitor:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run monitor
        env:
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          FROM_EMAIL: ${{ secrets.FROM_EMAIL }}
          NOTIFY_EMAIL: ${{ secrets.NOTIFY_EMAIL }}
        run: python monitor.py

      - name: Commit updated snapshots & Excel
        run: |
          git config user.name  "ads.txt Monitor"
          git config user.email "monitor@github-actions"
          git add snapshots.json adstxt_changes.xlsx
          git diff --cached --quiet || git commit -m "chore: update snapshots $(date -u +'%Y-%m-%d')"
          git push
