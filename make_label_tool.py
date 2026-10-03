"""
Evaluation, part 1: build a labelling tool for 50 job ads.

How it works, in plain words:
1. Take the newest Arbeitnow file and keep real data roles (same rules as extract_skills.py).
2. Pick 25 English and 25 German ads at random. A fixed "seed" makes the pick repeatable,
   so anyone running this on the same file gets the same 50 ads.
3. Write labelling/label_tool.html: a page you open in your browser. It shows one ad at a time
   with a tick box per skill. Your ticks are the "ground truth" that the rules (and later an AI)
   are scored against.
4. When you're done, the page downloads labels.csv. Put it in the labelling folder.

The rules' own answers are NOT shown in the tool, so they can't influence your labels.
"""

import glob
import html
import json
import os

import pandas as pd

from extract_skills import job_role

SEED = 42
PER_LANGUAGE = 25
OUT_DIR = "labelling"

# The skills you label. Names match extract_skills.py, so the scores line up later.
LABEL_SKILLS = [
    "SQL", "Python", "R", "Excel", "Power BI", "Tableau",
    "Statistics", "Machine learning", "AI / LLMs", "A/B testing",
    "ETL / data pipelines", "Data modelling", "Data visualisation",
    "Stakeholder management", "German required",
]


def main() -> None:
    files = sorted(glob.glob("data/arbeitnow_raw_*.csv"))
    if not files:
        raise SystemExit("No Arbeitnow file found. Run fetch_arbeitnow.py first.")
    jobs = pd.read_csv(files[-1], encoding="utf-8-sig")
    jobs = jobs[jobs["title"].fillna("").apply(job_role) != "Other (title mentions data)"]

    picks = []
    for lang in ("en", "de"):
        pool = jobs[jobs["language"] == lang]
        n = min(PER_LANGUAGE, len(pool))
        picks.append(pool.sample(n=n, random_state=SEED))
    sample = pd.concat(picks).sample(frac=1, random_state=SEED)  # mix the two languages

    os.makedirs(OUT_DIR, exist_ok=True)
    sample[["job_id", "language", "title", "company", "url"]].to_csv(
        f"{OUT_DIR}/sample.csv", index=False, encoding="utf-8-sig")

    ads = [{"id": r.job_id, "lang": r.language, "title": r.title, "company": r.company,
            "url": r.url, "text": r.description} for r in sample.itertuples()]
    template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "labelling", "template.html"),
                    encoding="utf-8").read()
    page = (template
            .replace("/*__ADS__*/[]", json.dumps(ads, ensure_ascii=False))
            .replace("/*__SKILLS__*/[]", json.dumps(LABEL_SKILLS))
            .replace("__SOURCE__", html.escape(os.path.basename(files[-1]))))
    with open(f"{OUT_DIR}/label_tool.html", "w", encoding="utf-8") as f:
        f.write(page)

    counts = sample["language"].value_counts().to_dict()
    print(f"Picked {len(sample)} ads ({counts.get('en', 0)} English, {counts.get('de', 0)} German) from {files[-1]}")
    print(f"Open {OUT_DIR}/label_tool.html in your browser to start labelling.")


if __name__ == "__main__":
    main()
