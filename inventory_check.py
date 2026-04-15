import os, json, requests, datetime

# ─────────────────────────────────────────────────────────────
# Add or remove partner domains here
# ─────────────────────────────────────────────────────────────
PARTNERS = [
    {"name": "DirecTV Stream",  "url": "https://streamtv.directv.com/app-ads.txt"},
    {"name": "Philo (help)",    "url": "https://help.philo.com/app-ads.txt"},
    {"name": "Philo",           "url": "https://philo.com/app-ads.txt"},
    {"name": "AdGRX TV Plus",   "url": "https://tvplus.adgrx.com/app-ads.txt"},
    {"name": "Tablo TV",        "url": "https://tablotv.com/app-ads.txt"},
    {"name": "Charter",         "url": "https://charter.net/app-ads.txt"},
    {"name": "Sling",           "url": "https://sling.com/app-ads.txt"},
    {"name": "Spectrum",        "url": "https://spectrum.net/app-ads.txt"},
]

REQUIRED_LINE = "inventorypartnerdomain=amc.com"
SNAPSHOTS_FILE = "inventory_snapshots.json"
HTML_FILE = "inventory.html"


def fetch(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "adstxt-monitor/1.0"})
        r.raise_for_status()
        return {"ok": True, "text": r.text.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_line(text):
    """Return True if inventorypartnerdomain=amc.com appears (case-insensitive)."""
    for line in (text or "").splitlines():
        if line.strip().lower() == REQUIRED_LINE:
            return True
    return False


def find_all_inventory_partners(text):
    """Return all inventorypartnerdomain= values found in the file."""
    found = []
    for line in (text or "").splitlines():
        s = line.strip().lower()
        if s.startswith("inventorypartnerdomain="):
            val = s.split("=", 1)[1].strip()
            if val:
                found.append(val)
    return found


def load_snapshots():
    if os.path.exists(SNAPSHOTS_FILE):
        with open(SNAPSHOTS_FILE) as f:
            return json.load(f)
    return {}


def save_snapshots(data):
    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_html(results, now_str):
    ok_count      = sum(1 for r in results if r["has_amc"])
    missing_count = sum(1 for r in results if r["ok"] and not r["has_amc"])
    error_count   = sum(1 for r in results if not r["ok"])

    rows = ""
    for r in results:
        if not r["ok"]:
            status_cell = '<td style="padding:12px 16px;text-align:center"><span style="background:#FFF2CC;color:#7B6000;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600">ERROR</span></td>'
            detail_cell = f'<td style="padding:12px 16px;font-size:12px;color:#7B6000">{esc(r["error"])}</td>'
            row_bg = ""
        elif r["has_amc"]:
            status_cell = '<td style="padding:12px 16px;text-align:center"><span style="background:#E2EFDA;color:#375623;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600">✓ FOUND</span></td>'
            others = [v for v in r["all_partners"] if v != "amc.com"]
            detail_cell = f'<td style="padding:12px 16px;font-size:12px;color:#375623">inventorypartnerdomain=amc.com present' + (f'<br><span style="color:#888">Also declares: {", ".join(others)}</span>' if others else "") + '</td>'
            row_bg = ""
        else:
            status_cell = '<td style="padding:12px 16px;text-align:center"><span style="background:#FCE4D6;color:#843C0C;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600">✗ MISSING</span></td>'
            others = r["all_partners"]
            detail_cell = '<td style="padding:12px 16px;font-size:12px;color:#843C0C">inventorypartnerdomain=amc.com NOT found' + (f'<br><span style="color:#888">Declares: {", ".join(others)}</span>' if others else '<br><span style="color:#888">No inventorypartnerdomain lines found</span>') + '</td>'
            row_bg = 'style="background:#fffafa"'

        rows += f'''<tr {row_bg}>
          <td style="padding:12px 16px;font-weight:500">{esc(r["name"])}</td>
          <td style="padding:12px 16px;font-family:monospace;font-size:12px;color:#555"><a href="{esc(r["url"])}" style="color:#1F3864" target="_blank">{esc(r["url"].replace("https://",""))}</a></td>
          {status_cell}
          {detail_cell}
          <td style="padding:12px 16px;font-size:12px;color:#999">{r["checked_at"]}</td>
        </tr>'''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inventory Partner Domain Check</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
  body {{ font-family: Arial, sans-serif; background: #f4f6f9; color: #1a1a2e; font-size: 14px }}
  header {{ background: #1F3864; color: #fff; padding: 24px 32px }}
  header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px }}
  header p {{ color: #BDD7EE; font-size: 13px }}
  header a {{ color: #BDD7EE }}
  .stats {{ display: flex; gap: 16px; padding: 20px 32px; background: #fff; border-bottom: 1px solid #e0e0e0; flex-wrap: wrap }}
  .stat {{ background: #f4f6f9; border-radius: 8px; padding: 12px 20px; min-width: 120px }}
  .stat-val {{ font-size: 24px; font-weight: 700 }}
  .stat-val.ok {{ color: #375623 }}
  .stat-val.bad {{ color: #843C0C }}
  .stat-val.warn {{ color: #7B6000 }}
  .stat-val.neutral {{ color: #1F3864 }}
  .stat-lbl {{ font-size: 12px; color: #666; margin-top: 2px }}
  main {{ max-width: 1100px; margin: 28px auto; padding: 0 20px 60px }}
  .card {{ background: #fff; border-radius: 10px; border: 1px solid #e0e0e0; overflow: hidden }}
  table {{ width: 100%; border-collapse: collapse }}
  thead tr {{ background: #f0f4fa }}
  th {{ padding: 10px 16px; text-align: left; font-size: 12px; color: #555; font-weight: 600 }}
  tbody tr:hover {{ background: #fafbfc }}
  tbody tr + tr td {{ border-top: 1px solid #f0f0f0 }}
</style>
</head>
<body>
<header>
  <h1>Inventory Partner Domain Check</h1>
  <p>Checking for <strong style="color:#fff">inventorypartnerdomain=amc.com</strong> in partner app-ads.txt files &nbsp;·&nbsp; Last checked: {now_str} &nbsp;·&nbsp; <a href="index.html">AMC monitor →</a></p>
</header>
<div class="stats">
  <div class="stat"><div class="stat-val neutral">{len(results)}</div><div class="stat-lbl">Partners checked</div></div>
  <div class="stat"><div class="stat-val ok">{ok_count}</div><div class="stat-lbl">✓ AMC declared</div></div>
  <div class="stat"><div class="stat-val bad">{missing_count}</div><div class="stat-lbl">✗ AMC missing</div></div>
  <div class="stat"><div class="stat-val warn">{error_count}</div><div class="stat-lbl">⚠ Errors</div></div>
</div>
<main>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>Partner</th>
          <th>app-ads.txt URL</th>
          <th style="text-align:center">Status</th>
          <th>Detail</th>
          <th>Last checked</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</main>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    snapshots = load_snapshots()
    results = []

    print(f"Checking {len(PARTNERS)} partners for inventorypartnerdomain=amc.com...")
    for p in PARTNERS:
        print(f"  {p['url'].replace('https://','')}", end=" ", flush=True)
        result = fetch(p["url"])
        if result["ok"]:
            has_amc     = check_line(result["text"])
            all_partners = find_all_inventory_partners(result["text"])
            status = "found" if has_amc else "missing"
            print(f"{'✓' if has_amc else '✗'} ({status})")
            entry = {
                "name": p["name"], "url": p["url"],
                "ok": True, "has_amc": has_amc,
                "all_partners": all_partners,
                "checked_at": now_str,
            }
        else:
            print(f"error: {result['error']}")
            entry = {
                "name": p["name"], "url": p["url"],
                "ok": False, "has_amc": False,
                "error": result["error"],
                "all_partners": [],
                "checked_at": now_str,
            }
        results.append(entry)
        snapshots[p["url"]] = entry

    save_snapshots(snapshots)
    generate_html(results, now_str)
    print(f"\nPage generated -> {HTML_FILE}")
    missing = [r for r in results if r["ok"] and not r["has_amc"]]
    if missing:
        print(f"\n⚠ MISSING inventorypartnerdomain=amc.com on {len(missing)} partner(s):")
        for r in missing:
            print(f"  - {r['name']} ({r['url']})")
    else:
        print("\n✓ All reachable partners correctly declare inventorypartnerdomain=amc.com")


if __name__ == "__main__":
    main()
