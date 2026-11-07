"""Draw the report's six figures (a storage and a speed figure per case group) from results/.

Bars are medians of the three cold samples with min-max whiskers; every axis starts at 0. The L10
line uses results/layerfs-L10.growth (LayerFS Store size on disk after every commit) and ovnfs's
per-commit size from its run1 sample, both measured as allocated bytes.
"""
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

import tables  # noqa: E402

HERE = Path(__file__).resolve().parent
OV, LF = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#52514e", "#898781", "#e1e0d9"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9, "svg.fonttype": "none",
                     "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": INK, "axes.titlesize": 10, "axes.titlecolor": "#0b0b0b",
                     "axes.titlelocation": "left", "svg.hashsalt": "cold"})


def tri(values):
    v = sorted(values)
    return v[1], v[0], v[2]


def bars(ax, title, cases, ov, lf, unit_fmt=lambda v: f"{v:,.0f}"):
    """Horizontal grouped bars, ovnfs above LayerFS in each case row, with min-max whiskers."""
    h = 0.36
    span = max(d[2] for d in ov + lf)
    for i, (name, data, color) in enumerate((("ovnfs", ov, OV), ("LayerFS", lf, LF))):
        ys = [k + (i - 0.5) * h for k in range(len(cases))]
        med = [d[0] for d in data]
        ax.barh(ys, med, height=h * 0.92, color=color, label=name)
        for y, (m, lo, hi) in zip(ys, data):
            if hi - lo > span * 0.005:  # a range too small to see is not drawn
                ax.plot([lo, hi], [y, y], color=INK, lw=1)
                ax.plot([lo, lo], [y - 0.07, y + 0.07], color=INK, lw=1)
                ax.plot([hi, hi], [y - 0.07, y + 0.07], color=INK, lw=1)
            ax.annotate(unit_fmt(m), (max(m, hi), y), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=INK)
    ax.set_yticks(range(len(cases)), cases)
    ax.invert_yaxis()
    ax.set_xlim(0, max(d[2] for d in ov + lf) * 1.22)
    ax.set_title(title)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)


def collect(d, cases, key, f=1.0, per_commit=False):
    ov, lf = [], []
    for c in cases:
        for arm, dst in (("ovnfs", ov), ("layerfs", lf)):
            ps = d[c][arm]["per_sample"]
            vals = [(p[key] / p["commits"] if per_commit else p[key]) * f for p in ps]
            dst.append(tri(vals))
    return ov, lf


def pct_of_raw(d, cases):
    ov, lf = [], []
    for c in cases:
        raw = d[c]["logical"]["raw"]
        for arm, dst in (("ovnfs", ov), ("layerfs", lf)):
            dst.append(tri([p["stored_at_end"] / raw * 100 for p in d[c][arm]["per_sample"]]))
    return ov, lf


def legend(fig):
    handles = [plt.Rectangle((0, 0), 1, 1, color=OV), plt.Rectangle((0, 0), 1, 1, color=LF)]
    fig.legend(handles, ["ovnfs", "LayerFS"], loc="upper right", ncol=2, frameon=False, fontsize=9)


def save(fig, name):
    fig.savefig(HERE / name, metadata={"Date": None})
    if os.environ.get("CHARTS_PNG"):  # preview copies, not published
        fig.savefig(Path(os.environ["CHARTS_PNG"]) / (name + ".png"), dpi=110)
    plt.close(fig)


def speed(d, cases, title, name):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 0.55 * len(cases) + 1.3), layout="constrained")
    bars(axs[0], "Exec: file operation (ms)", cases, *collect(d, cases, "apply_ms"), lambda v: f"{v:,.0f}")
    bars(axs[1], "Commit, cold (ms)", cases, *collect(d, cases, "commit_ms"), lambda v: f"{v:,.0f}")
    fig.suptitle(title + ": speed", x=0.01, ha="left", fontsize=11)
    legend(fig)
    save(fig, name)


def main():
    d = {c: {a: tables.arm(c, a) for a in ("ovnfs", "layerfs")} for c in tables.SMALL + tables.LARGE + tables.EDITS}
    for c in d:
        d[c]["logical"] = tables.logical(c)

    hist = list(tables.SMALL)
    title = "History: small code edits on several branches (S1-S4)"
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 0.55 * len(hist) + 1.3), layout="constrained")
    bars(axs[0], "Added per commit (KB)", hist, *collect(d, hist, "stored_by_commits", 1e-3, True), lambda v: f"{v:.1f}")
    bars(axs[1], "Stored at end (MB)", hist, *collect(d, hist, "stored_at_end", 1e-6), lambda v: f"{v:.1f}")
    fig.suptitle(title + ": storage", x=0.01, ha="left", fontsize=11)
    legend(fig)
    save(fig, "history-storage.svg")
    speed(d, hist, title, "history-speed.svg")

    edits = ["L100", "L10", "I10", "A5", "L500"]
    title = "Large file, small edits (L100, L10, I10, A5, L500)"
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.2), layout="constrained")
    g = json.loads((HERE / "results" / "layerfs-L10.growth" / "state.json").read_text())
    o = json.loads((HERE / "results" / "ovnfs-L10.run1" / "state.json").read_text())
    oprobe = {p["label"]: p["allocated_bytes"] for p in o["probes"]}
    ov_line = [oprobe["branch"]] + [s["probe"]["allocated_bytes"] for s in o["steps"]]
    lf_line = [g["allocated_after_import"]] + [s["allocated_after"] for s in g["steps"]]
    ax = axs[0]
    ax.plot(range(len(ov_line)), [v / 1e6 for v in ov_line], color=OV, lw=2, marker="o", ms=2.5)
    ax.plot(range(len(lf_line)), [v / 1e6 for v in lf_line], color=LF, lw=2, ls=(0, (5, 2)), marker="o", ms=2.5)
    ax.text(len(ov_line) - 1, ov_line[-1] / 1e6, f" {ov_line[-1] / 1e6:.0f} MB", va="center", fontsize=7.5, color=INK)
    ax.text(len(lf_line) - 1, lf_line[-1] / 1e6, f" {lf_line[-1] / 1e6:.1f} MB", va="bottom", fontsize=7.5, color=INK)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, max(ov_line) / 1e6 * 1.1)
    ax.set_xlabel("commit (0 = before the first commit)")
    ax.set_title("L10 Store size on disk after each commit (MB)")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    bars(axs[1], "Stored at end, % of every version in full", edits, *pct_of_raw(d, edits), lambda v: f"{v:.0f}%")
    fig.suptitle(title + ": storage", x=0.01, ha="left", fontsize=11)
    legend(fig)
    save(fig, "large-file-storage.svg")
    speed(d, edits, title, "large-file-speed.svg")

    big = list(tables.LARGE[:4])
    title = "500 MiB create, append, remove, cut"
    fig, ax = plt.subplots(1, 1, figsize=(5.4, 0.55 * len(big) + 1.3), layout="constrained")
    bars(ax, "Stored by the commit (MB)", big, *collect(d, big, "stored_by_commits", 1e-6),
         lambda v: f"{v:,.0f}" if v >= 1 else f"{v * 1e3:.0f} KB")
    fig.suptitle("500 MiB cases: storage", x=0.01, ha="left", fontsize=11)
    legend(fig)
    save(fig, "big500-storage.svg")
    speed(d, big, title, "big500-speed.svg")

    rc = list(tables.READS)
    ov, lf = [], []
    for c in rc:
        for arm, dst in (("ovnfs", ov), ("layerfs", lf)):
            s = json.loads((HERE / "results" / f"{arm}-{c}.cold" / "state.json").read_text())
            dst.append(tri([r["read_ns"] / 1e9 for r in s["reads"]]))
    labels = ["RT0 tree", "RT40 tree +40", "RF0 500 MiB", "RF5 500 MiB +5"]
    fig, ax = plt.subplots(1, 1, figsize=(7.0, 0.55 * len(rc) + 1.3), layout="constrained")
    bars(ax, "Exec: read every byte, cold (s)", labels, ov, lf, lambda v: f"{v:.2f}")
    fig.suptitle("Read cases: speed", x=0.01, ha="left", fontsize=11)
    legend(fig)
    save(fig, "read-speed.svg")


if __name__ == "__main__":
    main()
