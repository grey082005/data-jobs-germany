"""
Step 5 of the job-market tracker: rebuild the public dashboard from the data.

How it works, in plain words:
1. Read the newest snapshot from history/skill_history.csv and history/market_history.csv.
2. Pack the numbers the dashboard needs into one small JSON object.
3. Put that object into dashboard/template.html and save the result as docs/index.html.

GitHub Pages serves docs/index.html as a public website, so the dashboard always shows
the same numbers as the history files, and it updates itself every week.
"""

import json
import os

import pandas as pd

TEMPLATE = "dashboard/template.html"
OUTPUT = "docs/index.html"
PLACEHOLDER = "/*__DATA__*/null"
LANGUAGE_RULES = {"German required", "English required"}   # shown as headline numbers, not as skills
TOP_SKILLS = 18
LEVEL_ORDER = ["Senior / Lead", "Mid / not stated", "Junior", "Intern / Working student"]


def latest(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["snapshot_date"] == df["snapshot_date"].max()]


def main() -> None:
    skills = latest(pd.read_csv("history/skill_history.csv", encoding="utf-8-sig"))
    market = latest(pd.read_csv("history/market_history.csv", encoding="utf-8-sig")).iloc[0]

    ranked = skills[~skills["skill"].isin(LANGUAGE_RULES)].sort_values("share_all_%", ascending=False)
    data = {
        "date": market["snapshot_date"],
        "n_jobs": int(market["data_roles"]),
        "n_en": int(market["english_postings"]),
        "n_de": int(market["german_postings"]),
        "skills_searched": int(skills["skill"].nunique() - len(LANGUAGE_RULES)),
        "german_required_en": float(market["german_required_in_english_postings_%"]),
        "german_required_de": float(market["german_required_in_german_postings_%"]),
        "visa": int(market["visa_sponsorship"]),
        "skills": [
            {"name": r["skill"], "jobs": int(r["jobs_mentioning"]), "all": float(r["share_all_%"]),
             "en": float(r["share_english_postings_%"]), "de": float(r["share_german_postings_%"])}
            for _, r in ranked.head(TOP_SKILLS).iterrows()
        ],
        "roles": sorted(
            [[col.removeprefix("role: "), int(market[col])] for col in market.index
             if col.startswith("role: ") and pd.notna(market[col])],
            key=lambda pair: -pair[1],
        ),
        "levels": [[name, int(market[f"level: {name}"])] for name in LEVEL_ORDER
                   if f"level: {name}" in market.index and pd.notna(market[f"level: {name}"])],
    }
    if not data["levels"]:
        raise SystemExit("history/market_history.csv has no level columns yet. Run update_history.py first.")

    template = open(TEMPLATE, encoding="utf-8").read()
    if PLACEHOLDER not in template:
        raise SystemExit(f"{TEMPLATE} is missing the {PLACEHOLDER} placeholder.")
    page = "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n" \
           "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" \
           + template.replace(PLACEHOLDER, json.dumps(data, ensure_ascii=False), 1) \
           .replace("<div class=\"wrap\">", "</head>\n<body>\n<div class=\"wrap\">", 1) + "\n</body>\n</html>\n"

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Dashboard rebuilt for {data['date']}: {data['n_jobs']} data roles -> {OUTPUT}")


if __name__ == "__main__":
    main()
