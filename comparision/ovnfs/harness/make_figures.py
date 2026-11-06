#!/usr/bin/env python3
"""Draw figures/comparison.svg from results/summary.json (no dependencies).

Six small panels, one measure each, each with its own axis (no dual axes).
Colors: reference categorical slots 1 (blue, LayerFS) and 2 (orange, ovnfs),
validated with the dataviz validator for light and dark surfaces.
"""

import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DATA = json.loads((HERE / "results" / "summary.json").read_text())
CASES = ["S1", "S2", "S3", "S4"]
CASE_NOTE = {"S1": "1×40", "S2": "5 br×3", "S3": "4 forks×3", "S4": "5 same×1"}
ARMS = [("layerfs", "LayerFS v2.0.0", "s1"), ("ovnfs", "ovnfs", "s2")]


def row(case, arm):
    return DATA[f"{case}/{arm}"]


def per_commit_kb(case, arm):
    r = row(case, arm)
    if arm == "layerfs":
        return r["sum_new_stored"] / r["commits"] / 1000
    return (r["final_apparent"] - r["import_apparent"]) / r["commits"] / 1000


PANELS = [
    ("Total storage after the run", "MB", lambda c, a: row(c, a)["final"] / 1e6, 1),
    ("History added per commit (incl. new branches)", "KB", per_commit_kb, 1),
    ("Commit / snapshot latency, median", "ms", lambda c, a: row(c, a)["commit_med"], 0),
    ("Open a branch, median", "ms", lambda c, a: row(c, a)["branch_open_ms"], 0),
    ("Import the 65 MB base tree", "s", lambda c, a: row(c, a)["import_ms"] / 1000, 1),
    ("Read the whole tree in a fresh view, median", "s",
     lambda c, a: statistics.median(row(c, a)["verify_read_ms"]) / 1000, 1),
]

W, PW, PH = 960, 450, 238
LEFT, TOP = 20, 112
COLS, GAP_X, GAP_Y = 2, 20, 26
PLOT_L, PLOT_R, PLOT_T, PLOT_B = 52, 14, 46, 40


def nice_max(v):
    """Smallest clean tick step (1, 2, 2.5, 5 × 10^k) whose 4 ticks clear v + 12%."""
    for exp in range(-1, 6):
        for base in (1, 2, 2.5, 5):
            step = base * 10 ** exp
            if step * 4 >= v * 1.12:
                return step * 4, step
    return v, v / 4


def fmt(v, digits):
    if v >= 100:
        return f"{v:,.0f}"
    return f"{v:,.{digits}f}"


def bar_path(x, y0, w, h, r=4):
    """Column growing up from baseline y0: square bottom, 4px rounded top."""
    if h <= 0:
        return ""
    r = min(r, h, w / 2)
    top = y0 - h
    return (f"M{x:.1f},{y0:.1f} V{top + r:.1f} Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} "
            f"H{x + w - r:.1f} Q{x + w:.1f},{top:.1f} {x + w:.1f},{top + r:.1f} V{y0:.1f} Z")


def panel(ix, title, unit, value, digits):
    col, rowi = ix % COLS, ix // COLS
    ox, oy = LEFT + col * (PW + GAP_X), TOP + rowi * (PH + GAP_Y)
    vals = {(c, a): value(c, a) for c in CASES for a, _, _ in ARMS}
    vmax, step = nice_max(max(vals.values()))
    px0, px1 = ox + PLOT_L, ox + PW - PLOT_R
    py0, py1 = oy + PH - PLOT_B, oy + PLOT_T
    scale = (py0 - py1) / vmax
    out = [f'<text class="t-title" x="{ox}" y="{oy + 18}">{title}</text>',
           f'<text class="t-muted" x="{ox}" y="{oy + 34}">{unit}</text>']
    for k in range(5):
        y = py0 - k * step * scale
        out.append(f'<line class="grid" x1="{px0}" x2="{px1}" y1="{y:.1f}" y2="{y:.1f}"/>')
        label = fmt(k * step, 1 if step < 1 else 0)
        out.append(f'<text class="t-axis" x="{px0 - 6}" y="{y + 4:.1f}" text-anchor="end">{label}</text>')
    band = (px1 - px0) / len(CASES)
    bw, gap = 24, 2
    for i, c in enumerate(CASES):
        cx = px0 + band * i + band / 2
        for j, (a, _, cls) in enumerate(ARMS):
            v = vals[(c, a)]
            x = cx - bw - gap / 2 if j == 0 else cx + gap / 2
            h = max(v * scale, 1.5)
            out.append(f'<path class="{cls}" d="{bar_path(x, py0, bw, h)}"><title>{c} {a}: '
                       f'{fmt(v, digits)} {unit}</title></path>')
            out.append(f'<text class="t-value" x="{x + bw / 2:.1f}" y="{py0 - h - 5:.1f}" '
                       f'text-anchor="middle">{fmt(v, digits)}</text>')
        out.append(f'<text class="t-axis" x="{cx:.1f}" y="{py0 + 16}" text-anchor="middle">{c}</text>')
        out.append(f'<text class="t-muted small" x="{cx:.1f}" y="{py0 + 30}" '
                   f'text-anchor="middle">{CASE_NOTE[c]}</text>')
    out.append(f'<line class="axis" x1="{px0}" x2="{px1}" y1="{py0}" y2="{py0}"/>')
    return "\n".join(out)


def main():
    rows = (len(PANELS) + COLS - 1) // COLS
    H = TOP + rows * (PH + GAP_Y) + 46
    style = """
  .bg{fill:#fcfcfb} .s1{fill:#2a78d6} .s2{fill:#eb6834}
  .grid{stroke:#e8e7e3;stroke-width:1} .axis{stroke:#c3c2b7;stroke-width:1}
  text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}
  .t-h1{font-size:19px;font-weight:600;fill:#0b0b0b} .t-sub{font-size:13px;fill:#52514e}
  .t-title{font-size:13.5px;font-weight:600;fill:#0b0b0b} .t-muted{font-size:12px;fill:#7a7974}
  .t-axis{font-size:11.5px;fill:#52514e} .t-value{font-size:11px;fill:#0b0b0b}
  .t-legend{font-size:13px;fill:#0b0b0b} .small{font-size:10.5px}
  @media (prefers-color-scheme: dark){
    .bg{fill:#1a1a19} .s1{fill:#3987e5} .s2{fill:#d95926}
    .grid{stroke:#2e2e2c} .axis{stroke:#55544f}
    .t-h1,.t-title,.t-value,.t-legend{fill:#f0efec} .t-sub,.t-axis{fill:#c3c2b7} .t-muted{fill:#9c9b93}
  }"""
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-labelledby="t d">',
             '<title id="t">LayerFS v2.0.0 vs ovnfs: storage and speed on four small history shapes</title>',
             '<desc id="d">Six column charts comparing LayerFS and ovnfs per case S1 to S4; '
             'values are listed in README.md.</desc>',
             f"<style>{style}</style>",
             f'<rect class="bg" x="0" y="0" width="{W}" height="{H}"/>',
             '<text class="t-h1" x="20" y="34">LayerFS v2.0.0 (Docker) vs ovnfs — fs-storage-history base tree</text>',
             '<text class="t-sub" x="20" y="56">Lower is better in every panel. S1 = 1 branch × 40 commits, '
             'S2 = 5 branches × 3, S3 = 4 nested forks × 3, S4 = 5 identical branches × 1.</text>']
    lx = 20
    for _, name, cls in ARMS:
        parts.append(f'<rect class="{cls}" x="{lx}" y="76" width="12" height="12" rx="3"/>')
        parts.append(f'<text class="t-legend" x="{lx + 18}" y="86.5">{name}</text>')
        lx += 18 + len(name) * 7.6 + 26
    for i, (title, unit, value, digits) in enumerate(PANELS):
        parts.append(panel(i, title, unit, value, digits))
    parts.append(f'<text class="t-muted" x="20" y="{H - 24}">Storage: LayerFS = SQLite file + WAL; '
                 'ovnfs = state directory, allocated bytes (ext4). Per commit: LayerFS Σ new_stored; '
                 'ovnfs apparent growth.</text>')
    parts.append(f'<text class="t-muted" x="20" y="{H - 8}">Timings: warm, one sample, Docker shared with '
                 'other sessions (1-min load 13–27) — diagnostic only. 2026-11-06, LayerFS b4fa173e40, '
                 'ovnfs cdb3fb6.</text>')
    parts.append("</svg>")
    out = HERE / "figures" / "comparison.svg"
    out.write_text("\n".join(parts) + "\n")
    print(out)


if __name__ == "__main__":
    main()
