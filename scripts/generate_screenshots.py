import math
from PIL import Image, ImageDraw, ImageFont
import os

W = 1280
H = 800

BG = (13, 17, 28)
CARD_BG = (22, 27, 41)
SIDEBAR_BG = (17, 22, 36)
ACCENT = (99, 102, 241)
ACCENT_LIGHT = (129, 140, 248)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
YELLOW = (251, 191, 36)
TEXT_PRIMARY = (226, 232, 240)
TEXT_SECONDARY = (148, 163, 184)
TEXT_MUTED = (100, 116, 139)
BORDER = (38, 44, 62)
CHART_BG = (30, 36, 52)
GRID_LINE = (38, 44, 62)


def rounded_rect(draw, xy, r, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def draw_card(draw, x, y, w, h, r=12):
    rounded_rect(draw, (x, y, x + w, y + h), r, fill=CARD_BG, outline=None)


def draw_sidebar(draw):
    draw.rectangle((0, 0, 220, H), fill=SIDEBAR_BG)
    try:
        logo_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        item_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        logo_font = ImageFont.load_default()
        item_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.text((30, 28), "RASTRO", fill=ACCENT_LIGHT, font=logo_font)
    draw.text((30, 54), "Bug Bounty Intelligence", fill=TEXT_MUTED, font=small_font)

    items = [
        ("\u2302  Dashboard", True),
        ("\u2699  Pipeline", False),
        ("\U0001F50D  Discoveries", False),
        ("\u2714  Validations", False),
        ("\U0001F4DD  Reports", False),
        ("\U0001F464  Identity", False),
        ("\U0001F4CA  Intelligence", False),
        ("\U0001F527  System", False),
        ("\u2699  Settings", False),
    ]

    active_bg = (30, 36, 52)

    for i, (label, active) in enumerate(items):
        iy = 90 + i * 44
        if active:
            draw.rectangle((0, iy, 220, iy + 38), fill=active_bg)
            draw.rectangle((0, iy, 3, iy + 38), fill=ACCENT)
        draw.text((30, iy + 10), label, fill=TEXT_PRIMARY if active else TEXT_SECONDARY, font=item_font)

    draw.text((30, H - 40), "v1.6.0 RC10", fill=TEXT_MUTED, font=small_font)
    draw.text((30, H - 24), "System Online", fill=GREEN, font=small_font)


def draw_topbar(draw):
    y = 0
    draw.rectangle((220, y, W, y + 56), fill=(13, 17, 28))
    draw.line((220, y + 56, W, y + 56), fill=BORDER, width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    draw.text((250, 17), "Executive Dashboard", fill=TEXT_PRIMARY, font=title_font)

    draw.rounded_rectangle((900, 14, 1050, 42), radius=6, fill=CARD_BG, outline=BORDER)
    draw.text((920, 23), "Search...", fill=TEXT_MUTED, font=font)

    draw.ellipse((1070, 18, 1086, 34), fill=ACCENT)
    draw.ellipse((1100, 18, 1116, 34), fill=GREEN)
    draw.ellipse((1130, 18, 1146, 34), fill=YELLOW)


def draw_stat_card(draw, x, y, w, h, label, value, color=ACCENT_LIGHT, sub="", trend=""):
    draw_card(draw, x, y, w, h)
    try:
        val_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        lab_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except:
        val_font = ImageFont.load_default()
        lab_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    draw.text((x + 16, y + 14), label, fill=TEXT_SECONDARY, font=lab_font)
    draw.text((x + 16, y + 40), str(value), fill=color, font=val_font)
    if sub:
        draw.text((x + 16, y + 74), sub, fill=TEXT_MUTED, font=sub_font)
    if trend:
        tc = GREEN if trend.startswith("+") else RED
        draw.text((x + w - 60, y + 16), trend, fill=tc, font=sub_font)


def draw_chart(draw, x, y, w, h, title=""):
    draw_card(draw, x, y, w, h)
    try:
        t_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        t_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    if title:
        draw.text((x + 16, y + 14), title, fill=TEXT_PRIMARY, font=t_font)

    cx = x + 50
    cy = y + 50
    cw = w - 65
    ch = h - 70

    draw.rectangle((cx, cy, cx + cw, cy + ch), fill=CHART_BG, outline=GRID_LINE)

    for i in range(1, 5):
        gy = cy + ch * i // 5
        draw.line((cx, gy, cx + cw, gy), fill=GRID_LINE, width=1)
        draw.text((cx - 30, gy - 6), ["100", "75", "50", "25"][i - 1], fill=TEXT_MUTED, font=label_font)

    bars = [
        (0.08, 0.62),
        (0.16, 0.35),
        (0.24, 0.78),
        (0.32, 0.50),
        (0.40, 0.88),
        (0.48, 0.42),
        (0.56, 0.71),
        (0.64, 0.55),
        (0.72, 0.92),
        (0.80, 0.38),
        (0.88, 0.65),
        (0.96, 0.80),
    ]

    bw = cw // len(bars) - 4
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]

    for i, (bx, val) in enumerate(bars):
        bx_pos = int(cx + bx * cw - bw // 2)
        bh = int(val * ch)
        by = cy + ch - bh
        rounded_rect(draw, (bx_pos, by, bx_pos + bw, by + bh), 3, fill=ACCENT)
        if i < len(days):
            draw.text((bx_pos, cy + ch + 4), days[i], fill=TEXT_MUTED, font=label_font)

    draw.text((cx, cy + ch + 18), "Last 12 days", fill=TEXT_MUTED, font=label_font)


def draw_table(draw, x, y, w, h, title=""):
    draw_card(draw, x, y, w, h)
    try:
        t_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        row_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        t_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        row_font = ImageFont.load_default()

    if title:
        draw.text((x + 16, y + 14), title, fill=TEXT_PRIMARY, font=t_font)

    columns = ["Target", "Severity", "Status", "Score"]
    col_widths = [180, 100, 100, 80]
    col_x = [x + 16]
    for cw in col_widths[:-1]:
        col_x.append(col_x[-1] + cw)

    ty = y + 42
    draw.line((x + 16, ty, x + w - 16, ty), fill=BORDER, width=1)

    headers = columns
    for i, h_text in enumerate(headers):
        draw.text((col_x[i], ty + 4), h_text, fill=TEXT_MUTED, font=header_font)

    rows = [
        ("api.example.com", "Critical", "Validated", "9.2"),
        ("app.test.org", "High", "Pending", "7.8"),
        ("dev.internal.net", "Medium", "Suspicious", "5.1"),
        ("admin.dashboard.io", "Critical", "Confirmed", "9.8"),
        ("cdn.assets.com", "Low", "Dismissed", "2.3"),
    ]

    severity_colors = {"Critical": RED, "High": (249, 115, 22), "Medium": YELLOW, "Low": GREEN}

    for ri, row in enumerate(rows):
        ry = ty + 30 + ri * 34
        if ri % 2 == 0:
            draw.rectangle((x + 12, ry - 4, x + w - 12, ry + 26), fill=(18, 23, 37))
        for ci, val in enumerate(row):
            c = severity_colors.get(val, TEXT_PRIMARY) if ci == 1 else TEXT_PRIMARY
            draw.text((col_x[ci], ry), val, fill=c, font=row_font)


def draw_pipeline_graph(draw, x, y, w, h, title=""):
    draw_card(draw, x, y, w, h)
    try:
        t_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        node_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        t_font = ImageFont.load_default()
        node_font = ImageFont.load_default()

    if title:
        draw.text((x + 16, y + 14), title, fill=TEXT_PRIMARY, font=t_font)

    stages = [
        ("PENDING", GREEN),
        ("DISCOVERY", ACCENT),
        ("SCORING", ACCENT),
        ("VALIDATION", ACCENT),
        ("REPORT", YELLOW),
        ("CLOSED", GREEN),
    ]

    n = len(stages)
    node_w = 110
    node_h = 36
    gap = (w - 32 - n * node_w) // (n - 1)
    if gap < 20:
        gap = 20
        node_w = (w - 32 - (n - 1) * gap) // n

    base_y = y + h // 2 - node_h // 2

    for i, (label, color) in enumerate(stages):
        nx = x + 16 + i * (node_w + gap)
        rounded_rect(draw, (nx, base_y, nx + node_w, base_y + node_h), 6, fill=color)
        draw.text((nx + 8, base_y + 11), label, fill=(0, 0, 0) if color == YELLOW else (255, 255, 255), font=node_font)

        if i < n - 1:
            arrow_x = nx + node_w
            arrow_y_c = base_y + node_h // 2
            draw.line((arrow_x + 2, arrow_y_c, arrow_x + gap - 4, arrow_y_c), fill=TEXT_MUTED, width=2)
            draw.polygon([
                (arrow_x + gap - 2, arrow_y_c),
                (arrow_x + gap - 8, arrow_y_c - 5),
                (arrow_x + gap - 8, arrow_y_c + 5),
            ], fill=TEXT_MUTED)

    draw.text((x + 16, y + h - 24), "Pipeline: 6/6 stages complete  \u25cf  0 active  \u25cf  333 tests passing",
              fill=TEXT_MUTED, font=node_font)


def draw_health_dots(draw, x, y, w, h, title=""):
    draw_card(draw, x, y, w, h)
    try:
        t_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        val_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        t_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        val_font = ImageFont.load_default()

    if title:
        draw.text((x + 16, y + 14), title, fill=TEXT_PRIMARY, font=t_font)

    items = [
        ("API", "Online", GREEN),
        ("Agents", "4/4", GREEN),
        ("Pipeline", "Idle", GREEN),
        ("Database", "OK", GREEN),
        ("Memory", "42%", YELLOW),
        ("CPU", "18%", GREEN),
    ]

    per_row = 3
    iw = (w - 32) // per_row
    ih = 50

    for i, (label, value, color) in enumerate(items):
        col = i % per_row
        row = i // per_row
        ix = x + 16 + col * iw
        iy = y + 44 + row * (ih + 8)

        draw.ellipse((ix + 4, iy + 6, ix + 16, iy + 18), fill=color)
        draw.text((ix + 24, iy + 4), label, fill=TEXT_SECONDARY, font=label_font)
        draw.text((ix + 24, iy + 24), value, fill=TEXT_PRIMARY, font=val_font)


def generate_screenshots():
    os.makedirs("screenshots", exist_ok=True)

    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        title_font = ImageFont.load_default()

    # 1. Dashboard Main
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_sidebar(draw)
    draw_topbar(draw)

    draw_stat_card(draw, 240, 72, 230, 100, "Active Targets", "24", ACCENT_LIGHT, "+3 today", "+14%")
    draw_stat_card(draw, 485, 72, 230, 100, "Open Findings", "47", RED, "12 critical", "+8%")
    draw_stat_card(draw, 730, 72, 230, 100, "Reports Today", "8", GREEN, "6 pending", "+22%")
    draw_stat_card(draw, 975, 72, 230, 100, "Conf. Score", "89.4%", YELLOW, "trending up", "+2.1%")

    draw_chart(draw, 240, 186, 500, 280, "Findings by Day")
    draw_table(draw, 755, 186, 485, 280, "Recent Findings")

    draw_pipeline_graph(draw, 240, 480, 1000, 150, "Pipeline Overview")
    draw_health_dots(draw, 240, 645, 1000, 135, "System Health")

    actions = [700, 745, 790]
    for i, ay in enumerate(actions):
        draw.ellipse((W - 40, ay, W - 24, ay + 16), fill=ACCENT if i == 0 else CARD_BG)

    img.save("screenshots/dashboard-main.png", "PNG")
    print("[OK] screenshots/dashboard-main.png")

    # 2. Pipeline Monitor
    img2 = Image.new("RGB", (W, H), BG)
    draw2 = ImageDraw.Draw(img2)
    draw_sidebar(draw2)
    draw_topbar_with_title(draw2, "Pipeline Monitor")
    draw_pipeline_graph(draw2, 240, 80, 1000, 140, "Active Pipeline")

    pipeline_details = [
        ("Target", "Status", "Progress", "ETA"),
        ("api.example.com", "VALIDATION", "78%", "2 min"),
        ("app.test.org", "SCORING", "45%", "5 min"),
        ("dev.internal.net", "DISCOVERY", "22%", "12 min"),
        ("admin.dashboard.io", "REPORT", "92%", "1 min"),
    ]

    draw_table(draw2, 240, 240, 1000, 200, "Pipeline Queue")
    draw_chart(draw2, 240, 460, 480, 280, "Pipeline Duration (min)")
    draw_chart(draw2, 740, 460, 500, 280, "Success Rate by Stage")

    img2.save("screenshots/pipeline-monitor.png", "PNG")
    print("[OK] screenshots/pipeline-monitor.png")

    # 3. Report Detail
    img3 = Image.new("RGB", (W, H), BG)
    draw3 = ImageDraw.Draw(img3)
    draw_sidebar(draw3)
    draw_topbar_with_title(draw3, "Report Detail")

    draw_card(draw3, 240, 72, 1000, 60)
    try:
        rf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except:
        rf = ImageFont.load_default()

    draw3.text((260, 86), "SQL Injection in login endpoint", fill=TEXT_PRIMARY, font=rf)

    satus_colors = {"Critical": RED, "High": (249, 115, 22), "Medium": YELLOW, "Low": GREEN}
    try:
        sf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    except:
        sf = ImageFont.load_default()
    draw3.rounded_rectangle((1080, 78, 1200, 98), radius=4, fill=RED)
    draw3.text((1095, 82), "CRITICAL", fill=(255, 255, 255), font=sf)

    details = [
        ("Target", "api.example.com/login"),
        ("Method", "POST"),
        ("Parameter", "username"),
        ("CWE", "CWE-89: SQL Injection"),
        ("CVSS", "9.8 / 10.0"),
        ("Discovered", "2026-06-27 14:23:05"),
    ]

    try:
        df = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        dv = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        df = ImageFont.load_default()
        dv = ImageFont.load_default()

    y_off = 155
    for i, (label, value) in enumerate(details):
        dy = y_off + i * 30
        draw3.text((260, dy), label, fill=TEXT_MUTED, font=df)
        draw3.text((400, dy), value, fill=TEXT_PRIMARY, font=dv)

    draw_card(draw3, 240, 340, 1000, 160)
    try:
        pf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        pf = ImageFont.load_default()

    proof_lines = [
        "POST /login HTTP/1.1",
        "Host: api.example.com",
        "Content-Type: application/x-www-form-urlencoded",
        "",
        "username=admin' OR '1'='1' --&password=test",
    ]
    for i, line in enumerate(proof_lines):
        draw3.text((260, 360 + i * 22), line, fill=TEXT_SECONDARY, font=pf)

    draw_card(draw3, 240, 520, 1000, 150)
    recommendation = [
        "Use parameterized queries / prepared statements",
        "Apply input validation on username field",
        "Implement WAF rule to block SQL injection patterns",
        "Add security header Content-Security-Policy",
    ]
    draw3.text((260, 540), "Recommendations", fill=TEXT_PRIMARY, font=title_font)
    for i, rec in enumerate(recommendation):
        draw3.text((260, 570 + i * 22), f"  {i + 1}. {rec}", fill=TEXT_SECONDARY, font=pf)

    img3.save("screenshots/report-detail.png", "PNG")
    print("[OK] screenshots/report-detail.png")

    # 4. Identity Center
    img4 = Image.new("RGB", (W, H), BG)
    draw4 = ImageDraw.Draw(img4)
    draw_sidebar(draw4)
    draw_topbar_with_title(draw4, "Identity Center")

    platforms = [
        ("HackerOne", "h1_user_12345", GREEN, "Connected"),
        ("Bugcrowd", "bc_researcher", GREEN, "Connected"),
        ("Intigriti", "inti_user_6789", YELLOW, "Token expires in 3d"),
        ("YesWeHack", "ywh_researcher", RED, "Disconnected"),
        ("Synack", "synack_user", GREEN, "Connected"),
    ]

    try:
        pf_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        pf_reg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        pf_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        pf_bold = ImageFont.load_default()
        pf_reg = ImageFont.load_default()
        pf_small = ImageFont.load_default()

    for i, (name, username, status_color, status_text) in enumerate(platforms):
        px = 260
        py = 90 + i * 70
        draw_card(draw4, px, py, 960, 58)
        draw4.text((px + 20, py + 12), name, fill=TEXT_PRIMARY, font=pf_bold)
        draw4.text((px + 20, py + 34), username, fill=TEXT_SECONDARY, font=pf_reg)
        draw4.ellipse((px + 240, py + 16, px + 248, py + 24), fill=status_color)
        draw4.text((px + 256, py + 14), status_text, fill=status_color, font=pf_small)

    draw4.text((260, 450), "Vault Status", fill=TEXT_PRIMARY, font=title_font)
    draw4.text((260, 478), "Encryption: AES-256-GCM  \u25cf  Last sync: 5 min ago  \u25cf  Safe submit: ON (never auto-submit)",
               fill=TEXT_SECONDARY, font=pf_reg)

    img4.save("screenshots/identity-center.png", "PNG")
    print("[OK] screenshots/identity-center.png")

    # 5. System Health
    img5 = Image.new("RGB", (W, H), BG)
    draw5 = ImageDraw.Draw(img5)
    draw_sidebar(draw5)
    draw_topbar_with_title(draw5, "System Health")

    metrics = [
        ("System Uptime", "14d 6h 32m", GREEN),
        ("API Requests (24h)", "12,847", ACCENT),
        ("Active Agents", "4 / 4", GREEN),
        ("Database Size", "47.2 MB", GREEN),
        ("Memory Usage", "2.1 / 8.0 GB", YELLOW),
        ("CPU Load", "18%", GREEN),
        ("Disk Usage", "34%", GREEN),
        ("Network In/Out", "142/89 MB", ACCENT),
    ]

    per_row = 4
    iw = 230
    ih = 80
    for i, (label, value, color) in enumerate(metrics):
        col = i % per_row
        row = i // per_row
        mx = 260 + col * (iw + 20)
        my = 90 + row * (ih + 16)
        draw_card(draw5, mx, my, iw, ih)
        try:
            lf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            vf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except:
            lf = ImageFont.load_default()
            vf = ImageFont.load_default()
        draw5.text((mx + 14, my + 10), label, fill=TEXT_SECONDARY, font=lf)
        draw5.text((mx + 14, my + 36), value, fill=color, font=vf)

    draw_chart(draw5, 260, 310, 480, 220, "Memory Usage (last 24h)")
    draw_chart(draw5, 760, 310, 460, 220, "Request Latency (ms)")

    draw5.text((260, 560), "Watchdog Status", fill=TEXT_PRIMARY, font=title_font)
    watchdog_items = [
        "\u2713  API Health Check: OK (32ms)",
        "\u2713  Agent Supervisor: 4/4 agents responsive",
        "\u2713  Scheduler: All jobs on schedule",
        "\u2713  EventBus: 0 stuck events",
        "\u2713  Auto-Heal: Active (last heal: 2h ago)",
    ]

    try:
        wf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except:
        wf = ImageFont.load_default()

    for i, item in enumerate(watchdog_items):
        draw5.text((260, 590 + i * 24), item, fill=GREEN, font=wf)

    img5.save("screenshots/system-health.png", "PNG")
    print("[OK] screenshots/system-health.png")


def draw_topbar_with_title(draw, title):
    y = 0
    draw.rectangle((220, y, W, y + 56), fill=(13, 17, 28))
    draw.line((220, y + 56, W, y + 56), fill=BORDER, width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    draw.text((250, 17), title, fill=TEXT_PRIMARY, font=title_font)

    draw.rounded_rectangle((900, 14, 1050, 42), radius=6, fill=CARD_BG, outline=BORDER)
    draw.text((920, 23), "Search...", fill=TEXT_MUTED, font=font)

    draw.ellipse((1070, 18, 1086, 34), fill=ACCENT)
    draw.ellipse((1100, 18, 1116, 34), fill=GREEN)
    draw.ellipse((1130, 18, 1146, 34), fill=YELLOW)


if __name__ == "__main__":
    generate_screenshots()
