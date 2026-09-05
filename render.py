#!/usr/bin/env python3
"""
Render a daily ICFINANCE Instagram post (market open or close) as a 1080x1080 PNG.

Usage:
    python3 render.py open  out.png
    python3 render.py close out.png

Reads live market data via yfinance. No news headline generation, no LLM calls -
the headline is templated directly from the real computed % move, so nothing on
the image can be a fabricated claim.
"""
import sys
import datetime
from PIL import Image, ImageDraw, ImageFont

W = H = 1080
PAD = 76
CONTENT_W = W - 2 * PAD

BG = (11, 11, 12)
FG = (245, 241, 230)


def rgba(op, color=FG):
    return color + (int(255 * op),)


def load_fonts():
    pf = lambda size, weight: _variable(f"fonts/PlayfairDisplay.ttf", size, weight)
    mn = lambda size, weight: _variable(f"fonts/Manrope.ttf", size, weight)
    return {
        "wordmark": pf(28, "SemiBold"),
        "headline": pf(76, "Bold"),
        "session": mn(20, "SemiBold"),
        "stat_label": mn(16, "SemiBold"),
        "stat_value": mn(34, "SemiBold"),
        "footer": mn(16, "Medium"),
        "disclaimer": mn(13, "Medium"),
        "mover_label": mn(17, "SemiBold"),
        "logo_dollar": pf(22, "Bold"),
    }


def _variable(path, size, weight):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def draw_tracked_text(draw, xy, text, font, fill, tracking=0.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        w = draw.textlength(ch, font=font)
        x += w + tracking
    return x


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_logo(draw, x, y, size=52, dollar_font=None):
    # eye: wide outline ellipse + pupil circle with a $ glyph inside
    w, h = size, size * 0.56
    top = y + (size - h) / 2
    draw.ellipse([x, top, x + w, top + h], outline=FG, width=2)
    r = h * 0.44
    cx, cy = x + w / 2, top + h / 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=FG, width=2)
    if dollar_font is not None:
        bbox = draw.textbbox((0, 0), "$", font=dollar_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), "$", font=dollar_font, fill=FG)
    return x + w


def draw_sparkline(base_img, x, y, up=True, w=28, h=16, color=FG):
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    if up:
        pts = [(1, 14), (8, 9), (14, 11), (20, 4), (27, 2)]
    else:
        pts = [(1, 2), (8, 7), (14, 5), (20, 12), (27, 14)]
    pts = [(x + px, y + py) for px, py in pts]
    d.line(pts, fill=color + (255,), width=2, joint="curve")
    ex, ey = pts[-1]
    d.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=color + (255,))
    return overlay


def draw_hero_illustration(base_img, x, y):
    """Skyline silhouette + rising chart line, 928x200, positioned at (x, y)."""
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    buildings = [
        (0, 138, 95, 50), (110, 103, 85, 85), (210, 148, 100, 40),
        (325, 78, 75, 110), (415, 123, 95, 65), (525, 48, 115, 140),
        (655, 113, 90, 75), (760, 88, 105, 100), (880, 133, 48, 55),
    ]
    for bx, by, bw, bh in buildings:
        d.rectangle([x + bx, y + by, x + bx + bw, y + by + bh], outline=rgba(0.14), width=2)

    chart_pts = [(0, 160), (115, 148), (230, 155), (345, 110), (460, 122),
                 (575, 68), (690, 86), (805, 40), (928, 22)]
    poly = [(x + px, y + py) for px, py in chart_pts] + [(x + 928, y + 188), (x + 0, y + 188)]
    d.polygon(poly, fill=rgba(0.08))
    line_pts = [(x + px, y + py) for px, py in chart_pts]
    d.line(line_pts, fill=rgba(0.55), width=4, joint="curve")
    ex, ey = line_pts[-1]
    d.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], fill=rgba(0.9))
    return overlay


def render(session, data, out_path):
    assert session in ("open", "close")
    base = Image.new("RGB", (W, H), BG).convert("RGBA")
    solid = ImageDraw.Draw(base)
    fonts = load_fonts()
    overlays = []

    # header: logo + wordmark
    logo_end = draw_logo(solid, PAD, PAD, size=52, dollar_font=fonts["logo_dollar"])
    draw_tracked_text(solid, (logo_end + 18, PAD + 10), "ICFINANCE", fonts["wordmark"], FG, tracking=3)

    # hairline
    hl_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl_overlay).line([(PAD, PAD + 92), (W - PAD, PAD + 92)], fill=rgba(0.16), width=1)
    overlays.append(hl_overlay)

    # session tag
    session_label = "MARKET OPEN" if session == "open" else "MARKET CLOSE"
    tag_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tag_overlay)
    tx = PAD
    ty = PAD + 124
    tx = draw_tracked_text(td, (tx, ty), session_label, fonts["session"], rgba(1.0, FG), tracking=1.5) + 10
    td.text((tx, ty), "·", font=fonts["session"], fill=rgba(0.5))
    tx += td.textlength("· ", font=fonts["session"]) + 10
    td.text((tx, ty), "NYSE / NASDAQ", font=fonts["session"], fill=rgba(0.75))
    tx += td.textlength("NYSE / NASDAQ ", font=fonts["session"]) + 10
    td.text((tx, ty), "·", font=fonts["session"], fill=rgba(0.5))
    tx += td.textlength("· ", font=fonts["session"]) + 10
    td.text((tx, ty), data["session_time"], font=fonts["session"], fill=rgba(0.75))
    overlays.append(tag_overlay)

    # headline
    hy = PAD + 168
    lines = wrap_text(solid, data["headline"], fonts["headline"], CONTENT_W)
    for i, line in enumerate(lines[:2]):
        solid.text((PAD, hy + i * 88), line, font=fonts["headline"], fill=FG)
    hy_end = hy + len(lines[:2]) * 88

    # hero illustration
    hero_y = hy_end + 20
    overlays.append(draw_hero_illustration(base, PAD, hero_y))
    hero_bottom = hero_y + 200

    # stats row
    stats_top = hero_bottom + 40
    stats_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(stats_overlay)
    sd.line([(PAD, stats_top), (W - PAD, stats_top)], fill=rgba(0.16), width=1)
    row_bottom = stats_top + 108
    sd.line([(PAD, row_bottom), (W - PAD, row_bottom)], fill=rgba(0.16), width=1)
    overlays.append(stats_overlay)

    col_w = CONTENT_W // 3
    for i, s in enumerate(data["stats"]):
        cx = PAD + i * col_w
        solid.text((cx, stats_top + 28), s["label"], font=fonts["stat_label"], fill=(0, 0, 0, 0))
        lab_ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(lab_ov).text((cx, stats_top + 28), s["label"], font=fonts["stat_label"], fill=rgba(0.6))
        overlays.append(lab_ov)
        spark = draw_sparkline(base, cx, stats_top + 58, up=s["pct"] >= 0)
        overlays.append(spark)
        solid.text((cx + 36, stats_top + 52), f"{s['pct']:+.2f}%", font=fonts["stat_value"], fill=FG)

    y_cursor = row_bottom + 28
    if session == "close" and data.get("top_mover"):
        mv_ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
        md = ImageDraw.Draw(mv_ov)
        md.text((PAD, y_cursor), "TOP MOVER", font=fonts["mover_label"], fill=rgba(0.55))
        mx = PAD + md.textlength("TOP MOVER  ", font=fonts["mover_label"]) + 12
        md.text((mx, y_cursor), "·", font=fonts["mover_label"], fill=rgba(0.3))
        overlays.append(mv_ov)
        spark2 = draw_sparkline(base, int(mx) + 20, y_cursor - 2, up=data["top_mover"]["pct"] >= 0)
        overlays.append(spark2)
        solid.text((int(mx) + 56, y_cursor - 2), f"{data['top_mover']['symbol']} {data['top_mover']['pct']:+.1f}%",
                    font=fonts["mover_label"], fill=FG)
        y_cursor += 44

    # footer
    foot_ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(foot_ov)
    fy = H - PAD - 50
    fd.text((PAD, fy), data["date_str"], font=fonts["footer"], fill=rgba(0.55))
    dom = "icfinance.app"
    dw = fd.textlength(dom, font=fonts["footer"])
    fd.text((W - PAD - dw, fy), dom, font=fonts["footer"], fill=rgba(0.55))
    fd.text((PAD, fy + 32), "Educational content only · Not financial advice",
             font=fonts["disclaimer"], fill=rgba(0.35))
    overlays.append(foot_ov)

    for ov in overlays:
        base = Image.alpha_composite(base, ov)

    base.convert("RGB").save(out_path, "PNG")
    print(f"wrote {out_path}")


def build_caption(session, data):
    lines = [data["headline"], ""]
    for s in data["stats"]:
        arrow = "▲" if s["pct"] >= 0 else "▼"
        lines.append(f"{arrow} {s['name']}: {s['pct']:+.2f}%")
    lines += ["", "Follow @ic_finance_ for daily market open & close updates.",
              "", "#stockmarket #investing #trading #finance #wallstreet #sp500 #nasdaq"]
    return "\n".join(lines)


if __name__ == "__main__":
    import market_data
    session = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "output.png"
    data = market_data.get_data(session)
    render(session, data, out_path)
    with open(out_path + ".caption.txt", "w", encoding="utf-8") as f:
        f.write(build_caption(session, data))
