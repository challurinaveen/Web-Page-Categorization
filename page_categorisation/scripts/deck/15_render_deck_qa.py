"""Approximate renderer for QA: draws a .pptx slide by slide with real font metrics (Carlito=Calibri, Caladea=Cambria).
Reports text that overflows its box. Charts are drawn roughly (bars/lines + labels) - enough to spot crowding."""
import re, sys, os
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image, ImageDraw, ImageFont

PPTX, OUT = sys.argv[1], sys.argv[2]
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
DPI = 96
os.makedirs(OUT, exist_ok=True)
_fc = {}
def font(name, pt, bold):
    key = (name, round(pt * 4), bold)
    if key not in _fc:
        if name == "Cambria": f = "Caladea-Bold.ttf" if bold else "Caladea-Regular.ttf"
        elif name == "Courier New": f = None
        else: f = "Carlito-Bold.ttf" if bold else "Carlito-Regular.ttf"
        path = os.path.join(FD, f) if f else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        _fc[key] = ImageFont.truetype(path, max(6, int(round(pt * DPI / 72))))
    return _fc[key]
px = lambda e: e / 914400 * DPI
issues = []

def rgb(c, default=None):
    try: return "#" + str(c.rgb)
    except Exception: return default

def fill_of(sh):
    try:
        if sh.fill.type == 1:
            x = sh._element.xpath(".//p:spPr/a:solidFill/a:srgbClr")
            alpha = 1.0
            if x and x[0].xpath("./a:alpha"): alpha = int(x[0].xpath("./a:alpha/@val")[0]) / 100000
            return "#" + str(sh.fill.fore_color.rgb), alpha
    except Exception: pass
    return None, 1

def line_of(sh):
    try:
        if sh.line.fill.type == 1: return "#" + str(sh.line.color.rgb), max(1, int(sh.line.width / 12700 * DPI / 72))
    except Exception: pass
    return None, 1

def para_tokens(p, default_pt=13):
    toks = []
    for r in p.runs:
        f = r.font
        name = f.name or "Calibri"; pt = f.size.pt if f.size else default_pt; b = bool(f.bold)
        col = rgb(f.color, "#000000") if f.color and f.color.type else "#000000"
        for w in re.findall(r"\S+\s*|\s+", r.text):
            toks.append((w, name, pt, b, col))
    return toks

def layout_text(tf, w_px):
    """returns list of (line_tokens, line_h, align, indent, bullet, space_after) and total height"""
    lines = []; total = 0
    for p in tf.paragraphs:
        toks = para_tokens(p)
        ppr = p._p.pPr
        bullet = ppr is not None and (ppr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar") is not None)
        indent = 0.25 * DPI if bullet else 0
        spc = 0
        if ppr is not None:
            sa = ppr.xpath("./a:spcAft/a:spcPts/@val")
            if sa: spc = int(sa[0]) / 100 * DPI / 72
        al = p.alignment
        if not toks:
            lines.append(([], 14 * DPI / 72 * 1.2, al, indent, False, spc)); total += 14 * DPI / 72 * 1.2 + spc; continue
        cur, cw, first = [], 0, True
        def flush(last):
            nonlocal cur, cw, total, first
            lh = max(t[2] for t in cur) * DPI / 72 * 1.2 if cur else 14 * 1.2
            lines.append((cur, lh, al, indent, bullet and first, spc if last else 0)); total += lh + (spc if last else 0); first = False
            cur, cw = [], 0
        for t in toks:
            wlen = font(t[1], t[2], t[3]).getlength(t[0].rstrip()) if False else font(t[1], t[2], t[3]).getlength(t[0])
            wtrim = font(t[1], t[2], t[3]).getlength(t[0].rstrip())
            if cur and cw + wtrim > w_px - indent:
                flush(False)
            cur.append(t); cw += wlen
        flush(True)
    return lines, total

def draw_text(d, sh, x, y, w, h, name):
    tf = sh.text_frame
    bp = tf._txBody.bodyPr
    li = int(bp.get("lIns", 91440)); ri = int(bp.get("rIns", 91440)); ti = int(bp.get("tIns", 45720)); bi = int(bp.get("bIns", 45720))
    ix, iy, iw, ih = x + px(li), y + px(ti), w - px(li) - px(ri), h - px(ti) - px(bi)
    lines, total = layout_text(tf, iw)
    snippet = tf.text.replace("\n", " / ")[:42]
    if total > ih + 3: issues.append(f"{name}: text needs {total/DPI:.2f}in but box is {ih/DPI:.2f}in -> '{snippet}'")
    anchor = tf.vertical_anchor
    cy = iy + (0 if anchor in (None, MSO_ANCHOR.TOP) else (ih - total) / 2 if anchor == MSO_ANCHOR.MIDDLE else ih - total)
    for toks, lh, al, indent, bullet, spc in lines:
        lw = sum(font(t[1], t[2], t[3]).getlength(t[0]) for t in toks) - (font(toks[-1][1], toks[-1][2], toks[-1][3]).getlength(toks[-1][0]) - font(toks[-1][1], toks[-1][2], toks[-1][3]).getlength(toks[-1][0].rstrip()) if toks else 0)
        if toks and lw > iw - indent + 2: issues.append(f"{name}: a line is wider than its box -> '{snippet}'")
        cx = ix + indent
        if al == PP_ALIGN.CENTER: cx = ix + indent + (iw - indent - lw) / 2
        elif al == PP_ALIGN.RIGHT: cx = ix + iw - lw
        if bullet and toks: d.text((ix + 4, cy + (lh - toks[0][2] * DPI / 72) * 0.35), "•", font=font(toks[0][1], toks[0][2], False), fill=toks[0][4])
        for t in toks:
            f = font(t[1], t[2], t[3]); asc = f.getmetrics()[0]
            d.text((cx, cy + (lh - (asc + f.getmetrics()[1])) / 2), t[0].rstrip("\n"), font=f, fill=t[4])
            cx += f.getlength(t[0])
        cy += lh + spc
    if cy > y + h + 4: issues.append(f"{name}: drawn text runs {(cy-(y+h))/DPI:.2f}in past its shape -> '{snippet}'")

PAL = ["#2F6FED", "#0F766E", "#E08E1D", "#8FB1F2"]
def draw_chart(d, gf, x, y, w, h, name):
    ch = gf.chart
    plot = ch.plots[0]; cats = list(plot.categories); series = [(s.name, list(s.values)) for s in plot.series]
    kind = str(ch.chart_type)
    cols = []
    for i, s in enumerate(plot.series):
        c = None
        try:
            if s.format.fill.type == 1: c = "#" + str(s.format.fill.fore_color.rgb)
        except Exception: pass
        if c is None:
            try: c = "#" + str(s.format.line.color.rgb)
            except Exception: c = PAL[i % 4]
        cols.append(c)
    dark = False
    try:
        dark = bool(re.search(r"C3CDE0|DCEEFF", gf._element.xml))
    except Exception: pass
    tc = "#C3CDE0" if dark else "#5B6472"
    legend = ch.has_legend
    L, R, Tp, B = x + 0.5 * DPI, x + w - 0.15 * DPI, y + 0.15 * DPI, y + h - (0.35 + (0.3 if legend else 0)) * DPI
    f10 = font("Calibri", 10, False); f11 = font("Calibri", 11, False)
    allv = [v for _, vs in series for v in vs]
    horiz = "BAR_CLUSTERED" in kind and "COLUMN" not in kind
    vmax = float(max(100, max(allv))) if max(allv) <= 100 else max(allv)
    vmin = 20.0 if "LINE" in kind else 0.0
    vmax = 70.0 if "LINE" in kind else vmax
    if horiz: L = x + 2.0 * DPI
    # gridlines
    steps = 5
    for k in range(steps):
        vv = vmin + (vmax - vmin) * k / (steps - 1)
        if horiz:
            gx = L + (R - L) * (vv - vmin) / (vmax - vmin); d.line([(gx, Tp), (gx, B)], fill="#2A3B5E" if dark else "#E2DFD4"); d.text((gx - 8, B + 3), f"{vv:.0f}%", font=f10, fill=tc)
        else:
            gy = B - (B - Tp) * (vv - vmin) / (vmax - vmin); d.line([(L, gy), (R, gy)], fill="#2A3B5E" if dark else "#E2DFD4"); d.text((L - 34, gy - 7), f"{vv:.0f}%", font=f10, fill=tc)
    n, m = len(cats), len(series)
    if horiz:
        bandh = (B - Tp) / n
        for i, c in enumerate(cats):
            cy = B - bandh * (i + 0.5)
            lab = str(c); lw = f11.getlength(lab)
            if lw > 1.9 * DPI: issues.append(f"{name}: category label too wide '{lab}'")
            d.text((x + 0.05 * DPI, cy - 8), lab, font=f11, fill="#1B2435")
            for j, (sn, vs) in enumerate(series):
                bh = bandh * 0.6 / m; by = cy - bandh * 0.3 + j * bh
                ex = L + (R - L) * (vs[i] - vmin) / (vmax - vmin)
                d.rectangle([L, by, ex, by + bh], fill=cols[j]); d.text((ex + 4, by + bh / 2 - 7), f"{vs[i]:g}%", font=f11, fill="#1B2435")
    else:
        bandw = (R - L) / n
        for i, c in enumerate(cats):
            cx0 = L + bandw * i
            lab = str(c); lw = f11.getlength(lab)
            if lw > bandw - 2: issues.append(f"{name}: category label '{lab}' ({lw/DPI:.2f}in) wider than its slot ({bandw/DPI:.2f}in) - will wrap/rotate")
            d.text((cx0 + (bandw - min(lw, bandw)) / 2, B + 5), lab, font=f11, fill="#1B2435" if not dark else tc)
            if "LINE" in kind: continue
            gap = bandw * 0.25; bw = (bandw - gap) / m
            for j, (sn, vs) in enumerate(series):
                bx = cx0 + gap / 2 + j * bw; ty = B - (B - Tp) * (vs[i] - vmin) / (vmax - vmin)
                d.rectangle([bx, ty, bx + bw - 2, B], fill=cols[j]); lt = f"{vs[i]:g}%"
                d.text((bx + (bw - f10.getlength(lt)) / 2, ty - 15), lt, font=f10, fill="#1B2435")
                if f10.getlength(lt) > bw: issues.append(f"{name}: data label '{lt}' wider than its bar ({bw/DPI:.2f}in)")
        if "LINE" in kind:
            for j, (sn, vs) in enumerate(series):
                pts = [(L + bandw * (i + 0.5), B - (B - Tp) * (v - vmin) / (vmax - vmin)) for i, v in enumerate(vs)]
                d.line(pts, fill=cols[j], width=3)
                for (px_, py_), v in zip(pts, vs):
                    d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=cols[j]); d.text((px_ - 9, py_ - 18), f"{v:g}%", font=f10, fill="#F1F3F7" if dark else "#1B2435")
    if legend:
        lx = x + w / 2 - sum(f11.getlength(sn) + 28 for sn, _ in series) / 2
        for j, (sn, _) in enumerate(series):
            d.rectangle([lx, y + h - 22, lx + 12, y + h - 10], fill=cols[j]); d.text((lx + 16, y + h - 25), sn, font=f11, fill=tc); lx += f11.getlength(sn) + 28

def draw_table(d, gf, x, y, w, h, name):
    tbl = gf.table; cw = [px(c.width) for c in tbl.columns]; cy = y
    for ri, row in enumerate(tbl.rows):
        rh = px(row.height); need = 0; cx = x
        cells = []
        for ci, cell in enumerate(row.cells):
            tf = cell.text_frame
            mar = px(cell.margin_left) + px(cell.margin_right)
            lines, tot = layout_text(tf, cw[ci] - mar)
            need = max(need, tot + px(cell.margin_top) + px(cell.margin_bottom)); cells.append((cell, lines, tot))
        if need > rh + 2: issues.append(f"{name}: row {ri} grows from {rh/DPI:.2f}in to {need/DPI:.2f}in (PowerPoint will auto-grow it)")
        rh = max(rh, need)
        for ci, (cell, lines, tot) in enumerate(cells):
            fc = "#FFFFFF"
            try:
                if cell.fill.type == 1: fc = "#" + str(cell.fill.fore_color.rgb)
            except Exception: pass
            d.rectangle([cx, cy, cx + cw[ci], cy + rh], fill=fc, outline="#E2DFD4")
            ty = cy + (rh - tot) / 2
            for toks, lh, al, ind, bul, sp in lines:
                tx = cx + px(cell.margin_left)
                for t in toks:
                    f = font(t[1], t[2], t[3]); asc, desc = f.getmetrics(); d.text((tx, ty + (lh - asc - desc) / 2), t[0].rstrip("\n"), font=f, fill=t[4]); tx += f.getlength(t[0])
                ty += lh
            cx += cw[ci]
        cy += rh
    if cy > 6.9 * DPI: issues.append(f"{name}: table bottom at {cy/DPI:.2f}in collides with the footer")

prs = Presentation(PPTX)
W, H = int(px(prs.slide_width)), int(px(prs.slide_height))
for si, slide in enumerate(prs.slides, 1):
    bgc = "#FFFFFF"
    m = re.search(r'<p:bg>.*?srgbClr val="([0-9A-Fa-f]{6})"', slide.slide_layout._element.xml, re.S)
    if m: bgc = "#" + m.group(1)
    img = Image.new("RGBA", (W, H), bgc); d = ImageDraw.Draw(img, "RGBA")
    for sh in slide.shapes:
        x, y, w, h = px(sh.left), px(sh.top), px(sh.width), px(sh.height)
        nm = f"s{si}:{sh.name}"
        if sh.shape_type == MSO_SHAPE_TYPE.CHART or (sh.has_chart if hasattr(sh, "has_chart") else False):
            draw_chart(d, sh, x, y, w, h, nm); continue
        if getattr(sh, "has_table", False) and sh.has_table:
            draw_table(d, sh, x, y, w, h, nm); continue
        fc, alpha = fill_of(sh); lc, lw_ = line_of(sh)
        geom = sh._element.xpath(".//a:prstGeom/@prst"); geom = geom[0] if geom else ""
        if geom == "line":
            d.line([(x, y), (x + w, y + h)], fill=lc or "#E2DFD4", width=1)
        elif fc or lc:
            col = None
            if fc:
                r_, g_, b_ = int(fc[1:3], 16), int(fc[3:5], 16), int(fc[5:7], 16)
                col = (r_, g_, b_, int(255 * alpha))
            if geom == "ellipse": d.ellipse([x, y, x + w, y + h], fill=col, outline=lc if lc and alpha == 1 else None)
            elif geom in ("roundRect",):
                adj = sh._element.xpath(".//a:prstGeom/a:avLst/a:gd/@fmla"); rad = (int(adj[0].split()[1]) / 100000 if adj else 0.16667) * min(w, h)
                d.rounded_rectangle([x, y, x + w, y + h], radius=rad, fill=col, outline=lc if lc else None)
            elif geom == "rightArrow": d.polygon([(x, y + h * .25), (x + w * .6, y + h * .25), (x + w * .6, y), (x + w, y + h / 2), (x + w * .6, y + h), (x + w * .6, y + h * .75), (x, y + h * .75)], fill=col)
            elif geom == "downArrow": d.polygon([(x + w * .25, y), (x + w * .75, y), (x + w * .75, y + h * .55), (x + w, y + h * .55), (x + w / 2, y + h), (x, y + h * .55), (x + w * .25, y + h * .55)], fill=col)
            else: d.rectangle([x, y, x + w, y + h], fill=col, outline=lc if lc else None)
        if sh.has_text_frame and sh.text_frame.text.strip():
            draw_text(d, sh, x, y, w, h, nm)
    img.convert("RGB").save(os.path.join(OUT, f"slide-{si:02d}.png"))
# contact sheets, 2x2
files = sorted(f for f in os.listdir(OUT) if f.startswith("slide-"))
for k in range(0, len(files), 4):
    sheet = Image.new("RGB", (W * 2 // 1, H * 2 // 1), "#888888")
    for j, f in enumerate(files[k:k + 4]):
        sheet.paste(Image.open(os.path.join(OUT, f)), ((j % 2) * W, (j // 2) * H))
    sheet.save(os.path.join(OUT, f"sheet-{k // 4 + 1}.png"))
print("\n".join(issues) if issues else "no overflow issues found"); print(len(files), "slides rendered")
