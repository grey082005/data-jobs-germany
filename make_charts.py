"""
Step 3 of the job-market tracker: turn the skill ranking into a chart.

How it works, in plain words:
1. Load the newest skill_ranking file from the data folder.
2. Leave out the two language requirements (they get their own finding)
   and keep the 15 most-mentioned skills.
3. Draw a "dumbbell" chart: one dot for English postings, one for German
   postings, joined by a line. The longer the line, the bigger the difference.
4. Save the chart as a PNG image in a "charts" folder, ready for your README.
"""

import glob
import os

import matplotlib.pyplot as plt
import pandas as pd

TOP_N = 15

# Soft colours, checked for colour-blind readability
ENGLISH_COLOUR = "#4f86d1"   # soft blue
GERMAN_COLOUR = "#ee7650"    # soft coral
BACKGROUND = "#faf8f5"       # warm off-white
TEXT = "#22211f"
MUTED_TEXT = "#7a786f"
LINE = "#d9d6cf"             # the line joining the two dots
ROW_STRIPE = "#f3f0ea"       # faint stripe on every other row, helps the eye follow a row

plt.rcParams["font.family"] = ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]


def newest_file(pattern: str) -> str:
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No file matching {pattern} found. Run extract_skills.py first.")
    return files[-1]


def main() -> None:
    in_path = newest_file("data/skill_ranking_*.csv")
    snapshot_date = in_path.split("_")[-1].replace(".csv", "")
    ranking = pd.read_csv(in_path, encoding="utf-8-sig")

    skills = ranking[~ranking["skill"].isin(["German required", "English required"])]
    top = skills.sort_values("share_all_%", ascending=False).head(TOP_N).reset_index(drop=True)
    en = top["share_english_postings_%"]
    de = top["share_german_postings_%"]
    rows = range(len(top))

    fig, ax = plt.subplots(figsize=(9, 7.6), dpi=220)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    for i in rows:
        if i % 2 == 0:
            ax.axhspan(i - 0.5, i + 0.5, color=ROW_STRIPE, zorder=0, linewidth=0)
        ax.plot([en[i], de[i]], [i, i], color=LINE, linewidth=2.5, solid_capstyle="round", zorder=1)

    ax.scatter(en, rows, s=95, color=ENGLISH_COLOUR, edgecolor=BACKGROUND, linewidth=1.5, zorder=3)
    ax.scatter(de, rows, s=95, color=GERMAN_COLOUR, edgecolor=BACKGROUND, linewidth=1.5, zorder=3)

    # Value labels: the smaller value goes left of its dot, the larger one right
    for i in rows:
        low, high = sorted([(en[i], ENGLISH_COLOUR), (de[i], GERMAN_COLOUR)])
        if round(low[0]) == round(high[0]):   # same value: one label is enough
            ax.text(high[0] + 1.6, i, f"{high[0]:.0f}%", ha="left", va="center", fontsize=8, color=MUTED_TEXT)
            continue
        ax.text(low[0] - 1.6, i, f"{low[0]:.0f}%", ha="right", va="center", fontsize=8, color=MUTED_TEXT)
        ax.text(high[0] + 1.6, i, f"{high[0]:.0f}%", ha="left", va="center", fontsize=8, color=MUTED_TEXT)

    ax.set_yticks(list(rows))
    ax.set_yticklabels(top["skill"], fontsize=10, color=TEXT)
    ax.set_ylim(len(top) - 0.5, -0.5)   # most common skill at the top
    ax.set_xlim(-6, max(en.max(), de.max()) + 8)
    ax.set_xticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=10)

    # Title, subtitle, colour key and source line
    fig.text(0.03, 0.955, "What data jobs in Germany ask for", fontsize=16, weight="bold", color=TEXT)
    fig.text(0.03, 0.918, "Share of job postings that mention each skill", fontsize=10.5, color=MUTED_TEXT)
    key = [plt.Line2D([], [], marker="o", linestyle="", markersize=9, color=c, label=l)
           for c, l in [(ENGLISH_COLOUR, "English postings"), (GERMAN_COLOUR, "German postings")]]
    fig.legend(handles=key, loc="upper left", bbox_to_anchor=(0.02, 0.905), ncol=2, frameon=False,
               fontsize=10, labelcolor=TEXT, handletextpad=0.3, columnspacing=1.6)
    fig.text(0.03, 0.02, f"Source: Arbeitnow job board API · data roles only · snapshot {snapshot_date}",
             fontsize=7.5, color=MUTED_TEXT)

    fig.subplots_adjust(left=0.3, right=0.97, top=0.85, bottom=0.06)
    os.makedirs("charts", exist_ok=True)
    out_path = f"charts/top_skills_{snapshot_date}.png"
    fig.savefig(out_path, facecolor=BACKGROUND)
    print(f"Saved chart to {out_path}")


if __name__ == "__main__":
    main()
