"""
Step 4 of the job-market tracker: keep a history, so we can show trends.

How it works, in plain words:
1. Read this run's results (the newest jobs_with_skills, skill_ranking and Adzuna files).
2. Turn them into a few summary numbers for this snapshot date.
3. Add those numbers to two history files in the "history" folder:
   - skill_history.csv:  one row per skill per snapshot
   - market_history.csv: one row per snapshot (job counts, languages, levels, visa)
4. If this date is already in the history (you ran it twice in one day),
   the old rows are replaced, so nothing is counted twice.

Only these summary numbers are saved in the history, never the job postings
themselves, so the repository stays small and doesn't republish anyone's ads.
"""

import glob
import os

import pandas as pd

HISTORY_DIR = "history"


def newest_file(pattern: str):
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def snapshot_date_of(path: str) -> str:
    return os.path.basename(path).rsplit("_", 1)[-1].replace(".csv", "")


def append_snapshot(path: str, new_rows: pd.DataFrame, date: str) -> pd.DataFrame:
    """Add new_rows to the history file at path, replacing any rows for the same date."""
    if os.path.exists(path):
        history = pd.read_csv(path, encoding="utf-8-sig")
        history = history[history["snapshot_date"] != date]
        history = pd.concat([history, new_rows], ignore_index=True)
    else:
        history = new_rows
    history = history.sort_values("snapshot_date", kind="stable")
    history.to_csv(path, index=False, encoding="utf-8-sig")
    return history


def main() -> None:
    skills_path = newest_file("data/jobs_with_skills_*.csv")
    ranking_path = newest_file("data/skill_ranking_*.csv")
    if not skills_path or not ranking_path:
        raise SystemExit("No results found. Run extract_skills.py first.")

    date = snapshot_date_of(skills_path)
    jobs = pd.read_csv(skills_path, encoding="utf-8-sig")
    data_jobs = jobs[jobs["role"] != "Other (title mentions data)"]
    english = data_jobs[data_jobs["language"] == "en"]
    german = data_jobs[data_jobs["language"] == "de"]

    os.makedirs(HISTORY_DIR, exist_ok=True)

    # 1) Skill history
    ranking = pd.read_csv(ranking_path, encoding="utf-8-sig")
    ranking.insert(0, "snapshot_date", date)
    ranking["n_jobs"] = len(data_jobs)
    ranking["n_english"] = len(english)
    ranking["n_german"] = len(german)
    skill_history = append_snapshot(f"{HISTORY_DIR}/skill_history.csv", ranking, date)

    # 2) Market history (one row per snapshot)
    entry_levels = ["Intern / Working student", "Junior"]
    row = {
        "snapshot_date": date,
        "data_roles": len(data_jobs),
        "english_postings": len(english),
        "german_postings": len(german),
        "entry_level": int(data_jobs["level"].isin(entry_levels).sum()),
        "senior_or_lead": int((data_jobs["level"] == "Senior / Lead").sum()),
        "visa_sponsorship": int(data_jobs["visa_sponsorship"].astype(str).str.lower().eq("true").sum()),
        "german_required_in_english_postings_%": round(100 * english["German required"].mean(), 1) if len(english) else None,
        "german_required_in_german_postings_%": round(100 * german["German required"].mean(), 1) if len(german) else None,
    }
    for role, count in data_jobs["role"].value_counts().items():
        row[f"role: {role}"] = int(count)

    # Adzuna numbers, if Adzuna ran on the same day
    adzuna_path = f"data/jobs_raw_{date}.csv"
    if os.path.exists(adzuna_path):
        adzuna = pd.read_csv(adzuna_path, encoding="utf-8-sig")
        row["adzuna_jobs"] = len(adzuna)
        if "language" in adzuna:
            row["adzuna_english"] = int((adzuna["language"] == "en").sum())
            row["adzuna_german"] = int((adzuna["language"] == "de").sum())

    market_history = append_snapshot(f"{HISTORY_DIR}/market_history.csv", pd.DataFrame([row]), date)

    snapshots = market_history["snapshot_date"].nunique()
    print(f"History updated for {date}: {snapshots} snapshot(s) so far, "
          f"{len(skill_history)} skill rows in total.")


if __name__ == "__main__":
    main()
