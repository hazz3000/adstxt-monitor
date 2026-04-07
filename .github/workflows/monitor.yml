name: ads.txt Monitor

on:
  schedule:
    - cron: "0 9 * * *"
  workflow_dispatch:

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
          GMAIL_USER: ${{ secrets.GMAIL_USER }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          NOTIFY_EMAIL: ${{ secrets.NOTIFY_EMAIL }}
        run: python monitor.py

      - name: Commit updated snapshots & Excel
        run: |
          git config user.name  "ads.txt Monitor"
          git config user.email "monitor@github-actions"
          git add snapshots.json adstxt_changes.xlsx
          git diff --cached --quiet || git commit -m "chore: update snapshots $(date -u +'%Y-%m-%d')"
          git push
