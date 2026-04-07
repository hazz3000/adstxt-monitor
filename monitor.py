import os, json, smtplib, requests, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

FILES = [
    "https://amc.com/ads.txt",
    "https://amc.com/app-ads.txt",
    "https://bbca.com/ads.txt",
    "https://bbca.com/app-ads.txt",
    "https://ifc.com/ads.txt",
    "https://ifc.com/app-ads.txt",
    "https://sundancetv.com/ads.txt",
    "https://sundancetv.com/app-ads.txt",
    "https://wetv.com/ads.txt",
    "https://wetv.com/app-ads.txt",
]

SNAPSHOTS_FILE = "snapshots.json"
EXCEL_FILE = "adstxt_changes.xlsx"
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
NOTIFY_EMAIL = os.environ["NOTIFY_EMAIL"]

HEADER_FILL = PatternFill("solid", start_color="1F3864")
CHANGED_FILL = PatternFill("solid", start_color="FCE4D6")
NEW_FILL     = PatternFill("solid", start_color="E2EFDA")
ERROR_FILL   = PatternFill("solid", start_color="FFF2CC")
ADD_FILL     = PatternFill("solid", start_color="E2EFDA")
DEL_FILL     = PatternFill("solid", start_color="FCE4D6")


def fetch(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "adstxt-monitor/1.0"})
        r.raise_for_status()
        return {"ok": True, "text": r.text.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_snapshots():
    if os.path.exists(SNAPSHOTS_FILE):
        with open(SNAPSHOTS_FILE) as f:
            return json.load(f)
    return {}


def save_snapshots(snapshots):
    with open(SNAPSHOTS_FILE, "w") as f:
        json.dump(snapshots, f, indent=2)


def diff_lines(old, new):
    old_lines = old.splitlines() if old else []
    new_lines = new.splitlines() if new else []
    old_set, new_set = set(old_lines), set(new_lines)
    added   = [l for l in new_lines if l not in old_set]
    removed = [l for l in old_lines if l not in new_set]
    return added, removed


def short(url):
    return url.replace("https://", "")


def style_header(ws, row, cols):
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font      = Font(bold=True, color="FFFFFF", name="Arial", size=10)
        cell.fill      = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def auto_width(ws, min_w=12, max_w=60):
    for col in ws.columns:
        length = max((len(str(c.value or "")) for c in col), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(length + 2, min_w), max_w)


def update_excel(results, snapshots, now_str):
    wb = load_workbook(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    if "Change Log" not in wb.sheetnames:
        ws_log = wb.create_sheet("Change Log", 0)
        ws_log.append(["Timestamp", "File", "Status", "Lines Added", "Lines Removed", "Added Lines", "Removed Lines"])
        style_header(ws_log, 1, 7)
        ws_log.row_dimensions[1].height = 20
    else:
        ws_log = wb["Change Log"]

    for url, result in results.items():
        prev_text = snapshots.get(url, {}).get("text")
        if result["ok"]:
            if prev_text is None:
                status = "First snapshot"
                added, removed, fill = [], [], NEW_FILL
            else:
                added, removed = diff_lines(prev_text, result["text"])
                status = "Changed" if (added or removed) else "Unchanged"
                fill   = CHANGED_FILL if (added or removed) else None
            row = [now_str, short(url), status, len(added), len(removed),
                   "\n".join(added[:20]) or "-", "\n".join(removed[:20]) or "-"]
        else:
            status = "Error"
            fill   = ERROR_FILL
            row    = [now_str, short(url), f"Error: {result['error']}", "", "", "", ""]

        ws_log.append(row)
        if fill:
            r = ws_log.max_row
            for c in range(1, 8):
                ws_log.cell(r, c).fill = fill
        ws_log.row_dimensions[ws_log.max_row].height = 15

    ws_log.column_dimensions["A"].width = 20
    ws_log.column_dimensions["B"].width = 35
    ws_log.column_dimensions["C"].width = 16
    ws_log.column_dimensions["D"].width = 13
    ws_log.column_dimensions["E"].width = 15
    ws_log.column_dimensions["F"].width = 60
    ws_log.column_dimensions["G"].width = 60
    ws_log.freeze_panes = "A2"

    if "Current Snapshot" in wb.sheetnames:
        del wb["Current Snapshot"]
    ws_snap = wb.create_sheet("Current Snapshot")
    ws_snap.append(["File", "Last Updated", "Line Count", "Status"])
    style_header(ws_snap, 1, 4)
    for url, result in results.items():
        if result["ok"]:
            ws_snap.append([short(url), now_str, len(result["text"].splitlines()), "OK"])
        else:
            ws_snap.append([short(url), now_str, "-", f"Error: {result['error']}"])
            ws_snap.cell(ws_snap.max_row, 4).fill = ERROR_FILL
    auto_width(ws_snap)
    ws_snap.freeze_panes = "A2"

    for url, result in results.items():
        if not result["ok"]:
            continue
        prev_text = snapshots.get(url, {}).get("text")
        if prev_text is None:
            continue
        added, removed = diff_lines(prev_text, result["text"])
        if not added and not removed:
            continue
        sname = short(url).replace("/", "_").replace(".", "_")[:31]
        if sname in wb.sheetnames:
            del wb[sname]
        ws_d = wb.create_sheet(sname)
        ws_d.append(["Type", "Line Content"])
        style_header(ws_d, 1, 2)
        for line in added:
            ws_d.append(["+ Added", line])
            r = ws_d.max_row
            for c in [1, 2]:
                ws_d.cell(r, c).fill = ADD_FILL
                ws_d.cell(r, c).font = Font(color="375623", name="Arial", size=9)
        for line in removed:
            ws_d.append(["- Removed", line])
            r = ws_d.max_row
            for c in [1, 2]:
                ws_d.cell(r, c).fill = DEL_FILL
                ws_d.cell(r, c).font = Font(color="843C0C", name="Arial", size=9)
        ws_d.column_dimensions["A"].width = 12
        ws_d.column_dimensions["B"].width = 80
        ws_d.freeze_panes = "A2"

    wb.save(EXCEL_FILE)


def build_email_html(results, snapshots, now_str):
    changes, errors, unchanged, fresh = [], [], [], []
    for url, result in results.items():
        prev = snapshots.get(url, {}).get("text")
        if not result["ok"]:
            errors.append((url, result["error"]))
        elif prev is None:
            fresh.append(url)
        else:
            added, removed = diff_lines(prev, result["text"])
            if added or removed:
                changes.append((url, added, removed))
            else:
                unchanged.append(url)

    def badge(text, color, bg):
        return f'<span style="background:{bg};color:{color};padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600">{text}</span>'

    rows = ""
    for url, added, removed in changes:
        rows += (f'<tr><td style="padding:10px 12px;font-family:monospace;font-size:12px">{short(url)}</td>'
                 f'<td style="padding:10px 12px;text-align:center">{badge("CHANGED","#843C0C","#FCE4D6")}</td>'
                 f'<td style="padding:10px 12px;text-align:center;color:#375623">+{len(added)}</td>'
                 f'<td style="padding:10px 12px;text-align:center;color:#843C0C">-{len(removed)}</td></tr>')
        if added:
            preview = "\n".join(added[:30]) + ("..." if len(added) > 30 else "")
            rows += (f'<tr><td colspan="4" style="padding:4px 12px 8px">'
                     f'<details><summary style="font-size:12px;cursor:pointer;color:#375623">Show {len(added)} added lines</summary>'
                     f'<pre style="background:#E2EFDA;padding:8px;font-size:11px;margin-top:6px;overflow-x:auto">{preview}</pre>'
                     f'</details></td></tr>')
        if removed:
            preview = "\n".join(removed[:30]) + ("..." if len(removed) > 30 else "")
            rows += (f'<tr><td colspan="4" style="padding:4px 12px 8px">'
                     f'<details><summary style="font-size:12px;cursor:pointer;color:#843C0C">Show {len(removed)} removed lines</summary>'
                     f'<pre style="background:#FCE4D6;padding:8px;font-size:11px;margin-top:6px;overflow-x:auto">{preview}</pre>'
                     f'</details></td></tr>')
    for url, err in errors:
        rows += (f'<tr><td style="padding:10px 12px;font-family:monospace;font-size:12px">{short(url)}</td>'
                 f'<td style="padding:10px 12px;text-align:center">{badge("ERROR","#7B6000","#FFF2CC")}</td>'
                 f'<td colspan="2" style="padding:10px 12px;font-size:12px;color:#7B6000">{err}</td></tr>')
    for url in unchanged:
        rows += (f'<tr style="color:#888"><td style="padding:8px 12px;font-family:monospace;font-size:12px">{short(url)}</td>'
                 f'<td style="padding:8px 12px;text-align:center">{badge("OK","#555","#eee")}</td><td colspan="2"></td></tr>')
    for url in fresh:
        rows += (f'<tr><td style="padding:8px 12px;font-family:monospace;font-size:12px">{short(url)}</td>'
                 f'<td style="padding:8px 12px;text-align:center">{badge("NEW","#1F3864","#BDD7EE")}</td>'
                 f'<td colspan="2" style="font-size:12px;color:#555">First snapshot saved</td></tr>')

    subject_tag = f"🔴 {len(changes)} change(s)" if changes else ("⚠️ errors" if errors else "✅ no changes")
    summary = f"{len(changes)} changed · {len(errors)} errors · {len(unchanged)} unchanged · {len(fresh)} new snapshots"

    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
            f'<body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px">'
            f'<div style="max-width:700px;margin:auto;background:#fff;border-radius:8px;overflow:hidden;border:1px solid #ddd">'
            f'<div style="background:#1F3864;padding:20px 24px">'
            f'<h1 style="color:#fff;margin:0;font-size:18px">ads.txt Monitor Report</h1>'
            f'<p style="color:#BDD7EE;margin:6px 0 0;font-size:13px">{now_str} · {summary}</p></div>'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr style="background:#F2F2F2;font-size:12px;color:#555">'
            f'<th style="padding:10px 12px;text-align:left">File</th>'
            f'<th style="padding:10px 12px">Status</th>'
            f'<th style="padding:10px 12px">Added</th>'
            f'<th style="padding:10px 12px">Removed</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<div style="padding:16px 24px;font-size:12px;color:#888;border-top:1px solid #eee">'
            f'Full diff details are attached in the Excel file. Sent daily by your GitHub Actions monitor.'
            f'</div></div></body></html>')

    return subject_tag, html


def send_email(subject_tag, html_body, now_str):
    subject = f"[ads.txt Monitor] {subject_tag} - {now_str}"
    msg = MIMEMultipart("mixed")
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    with open(EXCEL_FILE, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{EXCEL_FILE}"')
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())


def main():
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    snapshots = load_snapshots()

    print(f"Checking {len(FILES)} files...")
    results = {}
    for url in FILES:
        print(f"  {short(url)}", end=" ", flush=True)
        results[url] = fetch(url)
        print("ok" if results[url]["ok"] else "error")

    update_excel(results, snapshots, now_str)
    print(f"Excel updated -> {EXCEL_FILE}")

    subject_tag, html = build_email_html(results, snapshots, now_str)
    send_email(subject_tag, html, now_str)
    print(f"Email sent -> {NOTIFY_EMAIL}")

    for url, result in results.items():
        if result["ok"]:
            snapshots[url] = {"text": result["text"], "updated": now_str}
    save_snapshots(snapshots)
    print("Snapshots saved.")


if __name__ == "__main__":
    main()
