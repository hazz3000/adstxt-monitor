import os, json, requests, datetime
from pathlib import Path

# ─────────────────────────────────────────────
# ADD NEW COMPETITORS HERE — just append a new entry
# ─────────────────────────────────────────────
COMPETITORS = [
    {"name": "Disney",       "domain": "disney.com",           "ads_txt": "https://disney.com/ads.txt",           "color": "#1a78c2", "initial": "D"},
    {"name": "NBCUniversal", "domain": "nbcuniversal.com",     "ads_txt": "https://nbcuniversal.com/ads.txt",     "color": "#000000", "initial": "N"},
    {"name": "Hulu",         "domain": "hulu.com",             "ads_txt": "https://hulu.com/ads.txt",             "color": "#1ce783", "initial": "H"},
    {"name": "Peacock",      "domain": "peacocktv.com",        "ads_txt": "https://peacocktv.com/ads.txt",        "color": "#f2a900", "initial": "P"},
    {"name": "Paramount",    "domain": "paramount.com",        "ads_txt": "https://paramount.com/ads.txt",        "color": "#0064ff", "initial": "P"},
    {"name": "Discovery",    "domain": "discovery.com",        "ads_txt": "https://discovery.com/ads.txt",        "color": "#003087", "initial": "D"},
    {"name": "FX",           "domain": "fxnetworks.com",       "ads_txt": "https://fxnetworks.com/ads.txt",       "color": "#cc0000", "initial": "F"},
    {"name": "HBO Max",      "domain": "max.com",              "ads_txt": "https://max.com/ads.txt",              "color": "#002be7", "initial": "M"},
    {"name": "Plex",         "domain": "plex.tv",              "ads_txt": "https://plex.tv/ads.txt",              "color": "#e5a00d", "initial": "P"},
    {"name": "Philo",        "domain": "philo.com",            "ads_txt": "https://philo.com/ads.txt",            "color": "#4b0082", "initial": "P"},
    {"name": "Vizio",        "domain": "vizio.com",            "ads_txt": "https://vizio.com/ads.txt",            "color": "#00a0dc", "initial": "V"},
    {"name": "Spectrum",     "domain": "spectrum.com",         "ads_txt": "https://spectrum.com/ads.txt",         "color": "#0099d8", "initial": "S"},
]

COMP_SNAPSHOTS_FILE = "competitor_snapshots.json"
AMC_SNAPSHOTS_FILE  = "snapshots.json"


def fetch(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "adstxt-monitor/1.0"})
        r.raise_for_status()
        return {"ok": True, "text": r.text.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def parse_lines(text):
    """Return set of non-comment, non-empty normalised lines."""
    lines = set()
    for line in (text or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            lines.add(s.lower())
    return lines


def diff_lines(old_text, new_text):
    old = [l.strip() for l in (old_text or "").splitlines() if l.strip() and not l.strip().startswith("#")]
    new = [l.strip() for l in (new_text or "").splitlines() if l.strip() and not l.strip().startswith("#")]
    old_set, new_set = set(old), set(new)
    added   = [l for l in new if l not in old_set]
    removed = [l for l in old if l not in new_set]
    return added, removed


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_amc_lines():
    """Return normalised set of all lines currently in any AMC ads.txt snapshot."""
    snaps = load_json(AMC_SNAPSHOTS_FILE)
    amc_lines = set()
    for key, val in snaps.items():
        if "amc.com" in key and val.get("text"):
            amc_lines |= parse_lines(val["text"])
    return amc_lines


# ─────────────────────────────────────────────
# HTML generation helpers
# ─────────────────────────────────────────────
PAGE_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
  body { font-family: Arial, sans-serif; background: #f4f6f9; color: #1a1a2e; font-size: 14px; line-height: 1.5 }
  header { background: #1F3864; color: #fff; padding: 24px 32px }
  header h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px }
  header p { color: #BDD7EE; font-size: 13px }
  header a { color: #BDD7EE; }
  main { max-width: 1000px; margin: 28px auto; padding: 0 20px 60px }
  .section-title { font-size: 16px; font-weight: 600; color: #1F3864; margin: 28px 0 12px }
  .card { background: #fff; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 16px; overflow: hidden }
  .card-head { padding: 14px 20px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 12px }
  .logo-circle { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #fff; flex-shrink: 0 }
  .card-title { font-weight: 600; font-size: 15px }
  .card-sub { font-size: 12px; color: #888; font-family: monospace }
  .badge { font-size: 11px; padding: 2px 10px; border-radius: 20px; font-weight: 600; margin-left: auto }
  .badge.changed { background: #FCE4D6; color: #843C0C }
  .badge.ok { background: #f0f0f0; color: #666 }
  .badge.error { background: #FFF2CC; color: #7B6000 }
  .badge.new { background: #E2EFDA; color: #375623 }
  .card-body { padding: 14px 20px }
  .entry { border-radius: 6px; padding: 10px 14px; border-left: 3px solid #ddd; margin-bottom: 10px }
  .entry.changed { border-left-color: #E24B4A; background: #fff9f9 }
  .entry.ok { border-left-color: #ccc; background: #fafafa }
  .entry.error { border-left-color: #f0ad4e; background: #fffdf0 }
  .entry.new { border-left-color: #1D9E75; background: #f6fffa }
  .entry.opportunity { border-left-color: #7B2FBE; background: #f9f5ff }
  .entry-date { font-size: 12px; color: #999; margin-bottom: 3px }
  .entry-meta { font-size: 13px; color: #555; margin-bottom: 6px }
  .diff { border-radius: 4px; overflow: hidden; font-family: monospace; font-size: 12px }
  .line { padding: 2px 10px; white-space: pre-wrap; word-break: break-all }
  .line.add { background: #E2EFDA; color: #375623 }
  .line.del { background: #FCE4D6; color: #843C0C }
  .line.opp { background: #f0e6ff; color: #4a0080 }
  .opp-label { font-size: 11px; font-weight: 700; color: #7B2FBE; padding: 4px 10px; background: #e8d5ff; }
"""


def generate_competitor_page(comp, history, amc_lines, now_str):
    """Generate individual competitor detail page."""
    name    = comp["name"]
    domain  = comp["domain"]
    color   = comp["color"]
    initial = comp["initial"]
    entries = list(reversed(history))
    latest  = entries[0] if entries else None

    # Sales opportunities: lines in latest snapshot not in AMC
    opps = []
    if latest and latest.get("status") in ("changed", "first_snapshot", "unchanged") and latest.get("text"):
        comp_lines = parse_lines(latest["text"])
        opps = sorted(comp_lines - amc_lines)

    # Build timeline
    timeline_html = ""
    for e in entries:
        status = e.get("status", "")
        if status == "changed":
            added   = e.get("added", [])
            removed = e.get("removed", [])
            add_html = "".join(f'<div class="line add">+ {esc(l)}</div>' for l in added[:50])
            del_html = "".join(f'<div class="line del">- {esc(l)}</div>' for l in removed[:50])
            more_a = f'<div class="line add">… {len(added)-50} more added lines</div>' if len(added) > 50 else ""
            more_r = f'<div class="line del">… {len(removed)-50} more removed lines</div>' if len(removed) > 50 else ""
            meta = f'+{len(added)} added · -{len(removed)} removed · {e.get("lines","?")} lines total'
            timeline_html += f'<div class="entry changed"><div class="entry-date">{e["date"]}</div><div class="entry-meta">{meta}</div><div class="diff">{add_html}{more_a}{del_html}{more_r}</div></div>'
        elif status == "error":
            timeline_html += f'<div class="entry error"><div class="entry-date">{e["date"]}</div><div class="entry-meta">Error: {esc(e.get("error",""))}</div></div>'
        elif status == "first_snapshot":
            timeline_html += f'<div class="entry new"><div class="entry-date">{e["date"]}</div><div class="entry-meta">First snapshot saved · {e.get("lines","?")} lines</div></div>'
        else:
            timeline_html += f'<div class="entry ok"><div class="entry-date">{e["date"]}</div><div class="entry-meta">No changes · {e.get("lines","?")} lines</div></div>'

    # Opportunities section
    opp_html = ""
    if opps:
        opp_lines = "".join(f'<div class="line opp">{esc(l)}</div>' for l in opps[:100])
        more_opp = f'<div class="line opp">… {len(opps)-100} more lines</div>' if len(opps) > 100 else ""
        opp_html = f'''
        <div class="section-title">Sales opportunities — {len(opps)} lines {name} has that AMC does not</div>
        <div class="card">
          <div class="card-body">
            <div class="entry opportunity">
              <div class="entry-meta" style="margin-bottom:8px">These demand partners or lines appear in <strong>{domain}/ads.txt</strong> but not in any AMC ads.txt file. Potential partners to activate.</div>
              <div class="opp-label">Lines not in AMC</div>
              <div class="diff">{opp_lines}{more_opp}</div>
            </div>
          </div>
        </div>'''

    last_badge = ""
    if latest:
        bmap = {"changed": "changed", "unchanged": "ok", "error": "error", "first_snapshot": "new"}
        bcls = bmap.get(latest.get("status",""), "ok")
        blbl = {"changed": "Changed", "unchanged": "Unchanged", "error": "Error", "first_snapshot": "First snapshot"}.get(latest.get("status",""), "")
        last_badge = f'<span class="badge {bcls}">{blbl}</span>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — ads.txt Monitor</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header>
  <h1><span style="display:inline-flex;align-items:center;gap:12px">
    <span class="logo-circle" style="background:{color}">{initial}</span>
    {name} — ads.txt Monitor
  </span></h1>
  <p>Last updated: {now_str} &nbsp;·&nbsp; <a href="competitors.html">← All competitors</a> &nbsp;·&nbsp; <a href="index.html">AMC monitor</a></p>
</header>
<main>
  {opp_html}
  <div class="section-title">Change history — {domain}/ads.txt</div>
  <div class="card"><div class="card-body">{timeline_html}</div></div>
</main>
</body>
</html>"""

    slug = name.lower().replace(" ", "_")
    with open(f"competitor_{slug}.html", "w", encoding="utf-8") as f:
        f.write(html)
    return slug


def generate_landing_page(competitors_with_slugs, snapshots, now_str):
    """Generate the logo grid landing page."""
    cards = ""
    for comp, slug in competitors_with_slugs:
        name    = comp["name"]
        domain  = comp["domain"]
        color   = comp["color"]
        initial = comp["initial"]
        history = snapshots.get(domain, [])
        latest  = history[-1] if history else None

        if not latest:
            badge = '<span class="badge new">Not yet checked</span>'
        else:
            bmap = {"changed": "changed", "unchanged": "ok", "error": "error", "first_snapshot": "new"}
            bcls = bmap.get(latest.get("status",""), "ok")
            blbl = {"changed": "Changed", "unchanged": "Unchanged", "error": "Error", "first_snapshot": "First snapshot"}.get(latest.get("status",""), "")
            badge = f'<span class="badge {bcls}">{blbl}</span>'

        last_date = latest["date"] if latest else "—"
        cards += f'''
        <a href="competitor_{slug}.html" style="text-decoration:none;color:inherit">
          <div class="card" style="cursor:pointer;transition:border-color 0.15s" onmouseover="this.style.borderColor='#aaa'" onmouseout="this.style.borderColor='#e0e0e0'">
            <div class="card-head">
              <div class="logo-circle" style="background:{color}">{initial}</div>
              <div>
                <div class="card-title">{name}</div>
                <div class="card-sub">{domain}/ads.txt</div>
              </div>
              {badge}
            </div>
            <div class="card-body" style="font-size:12px;color:#888">Last checked: {last_date}</div>
          </div>
        </a>'''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Competitor ads.txt Monitor</title>
<style>
  {PAGE_CSS}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px }}
</style>
</head>
<body>
<header>
  <h1>Competitor ads.txt Monitor</h1>
  <p>Last updated: {now_str} &nbsp;·&nbsp; {len(COMPETITORS)} competitors tracked &nbsp;·&nbsp; Checked monthly &nbsp;·&nbsp; <a href="index.html">AMC monitor →</a></p>
</header>
<main>
  <div class="section-title">Click any competitor to see their ads.txt history and sales opportunities</div>
  <div class="grid">{cards}</div>
</main>
</body>
</html>"""

    with open("competitors.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    snapshots = load_json(COMP_SNAPSHOTS_FILE)
    amc_lines = get_amc_lines()

    print(f"Checking {len(COMPETITORS)} competitors...")
    for comp in COMPETITORS:
        domain = comp["domain"]
        url    = comp["ads_txt"]
        print(f"  {domain}", end=" ", flush=True)
        result = fetch(url)
        prev   = snapshots.get(domain, [])
        prev_text = prev[-1].get("text") if prev and prev[-1].get("status") in ("changed","unchanged","first_snapshot") else None

        if result["ok"]:
            if prev_text is None:
                entry = {"date": now_str, "status": "first_snapshot",
                         "text": result["text"], "lines": len(result["text"].splitlines())}
            else:
                added, removed = diff_lines(prev_text, result["text"])
                status = "changed" if (added or removed) else "unchanged"
                entry  = {"date": now_str, "status": status, "text": result["text"],
                          "lines": len(result["text"].splitlines()),
                          "added": added, "removed": removed}
            print(f"ok ({entry['status']})")
        else:
            entry = {"date": now_str, "status": "error", "error": result["error"]}
            print(f"error")

        if domain not in snapshots:
            snapshots[domain] = []
        snapshots[domain].append(entry)

    save_json(COMP_SNAPSHOTS_FILE, snapshots)
    print("Snapshots saved.")

    # Generate pages
    competitors_with_slugs = []
    for comp in COMPETITORS:
        history = snapshots.get(comp["domain"], [])
        slug = generate_competitor_page(comp, history, amc_lines, now_str)
        competitors_with_slugs.append((comp, slug))

    generate_landing_page(competitors_with_slugs, snapshots, now_str)
    print(f"Pages generated: competitors.html + {len(COMPETITORS)} detail pages")


if __name__ == "__main__":
    main()
