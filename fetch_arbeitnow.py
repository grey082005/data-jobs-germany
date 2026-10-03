"""
Step 1b of the job-market tracker:
fetch job postings WITH FULL DESCRIPTIONS from the free Arbeitnow API
(no API key needed) and keep only data-related jobs.

How it works, in plain words:
1. Go through Arbeitnow's job list page by page (the API has no search,
   so we collect everything and filter ourselves).
2. Do a second pass with the visa-sponsorship filter switched on, and
   remember which jobs offer visa sponsorship.
3. Keep only jobs whose title looks data-related (data, analyst, BI, ...).
4. Turn the HTML description into plain text and label its language.
5. Save the table as a CSV file named with today's date,
   plus one file with only English and one with only German postings.
"""

import html
import os
import re
import time
from datetime import date, datetime, timezone

import pandas as pd
import requests

# --- Settings you can change -------------------------------------------------

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 30   # safety limit, so the script never runs forever

# A job is kept if its title contains any of these words (lowercase)
DATA_TITLE_WORDS = [
    "data", "analyst", "analytics", "business intelligence", "bi ",
    "machine learning", "scientist", "insights", "reporting",
]

# --- Language detection (same idea as in fetch_jobs.py) ------------------------

GERMAN_WORDS = {"und", "der", "die", "das", "wir", "mit", "für", "sie", "ist", "oder", "bei", "ein", "eine", "zu", "von", "unser", "unsere", "kenntnisse", "erfahrung"}
ENGLISH_WORDS = {"and", "the", "we", "with", "for", "you", "is", "or", "at", "a", "an", "to", "of", "our", "your", "skills", "experience"}


def detect_language(text) -> str:
    """Return "de", "en" or "unknown" for a piece of text."""
    words = re.findall(r"[a-zäöüß]+", str(text).lower())
    german = sum(word in GERMAN_WORDS for word in words)
    english = sum(word in ENGLISH_WORDS for word in words)
    if german == english:
        return "unknown"
    return "de" if german > english else "en"


def html_to_text(raw_html) -> str:
    """Remove HTML tags like <p> and <li> so only the readable text is left."""
    text = re.sub(r"<[^>]+>", " ", str(raw_html or ""))
    text = html.unescape(text)             # turns &amp; into &, etc.
    return re.sub(r"\s+", " ", text).strip()  # squash extra spaces and line breaks


def is_data_job(title) -> bool:
    title = f" {str(title).lower()} "
    return any(word in title for word in DATA_TITLE_WORDS)


# --- Talking to the API --------------------------------------------------------

def fetch_page(page: int, visa_only: bool = False) -> dict:
    """Ask Arbeitnow for one page of jobs. Waits and retries if we're going too fast."""
    params = {"page": page}
    if visa_only:
        params["visa_sponsorship"] = "true"
    for attempt in range(3):
        response = requests.get(API_URL, params=params, timeout=30)
        if response.status_code == 429:   # "too many requests": wait, then try again
            time.sleep(10 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()
    return {}


def fetch_all(visa_only: bool = False) -> list[dict]:
    """Go through the pages until there are no more jobs (or MAX_PAGES is reached)."""
    jobs = []
    label = "visa-sponsorship jobs" if visa_only else "all jobs"
    for page in range(1, MAX_PAGES + 1):
        result = fetch_page(page, visa_only)
        batch = result.get("data", [])
        print(f"{label}, page {page}: {len(batch)} jobs")
        jobs.extend(batch)
        has_next = (result.get("links") or {}).get("next")
        if not batch or ("links" in result and not has_next):
            break  # reached the last page
        time.sleep(1)  # be polite to the API
    return jobs


def to_row(job: dict, visa_slugs: set) -> dict:
    """Turn one job from the API into one flat table row."""
    description = html_to_text(job.get("description"))
    created = job.get("created_at")
    return {
        "job_id": job.get("slug"),
        "title": job.get("title"),
        "company": job.get("company_name"),
        "location": job.get("location"),
        "remote": job.get("remote"),
        "job_types": ", ".join(job.get("job_types") or []),
        "tags": ", ".join(job.get("tags") or []),
        "visa_sponsorship": job.get("slug") in visa_slugs,
        "created": datetime.fromtimestamp(created, tz=timezone.utc).date().isoformat() if created else None,
        "description": description,   # the FULL text this time
        "language": detect_language(f"{job.get('title')} {description}"),
        "url": job.get("url"),
        "source": "arbeitnow",
        "fetched_on": date.today().isoformat(),
    }


def save_language_files(df: pd.DataFrame, prefix: str) -> None:
    """Save the English and the German postings into two separate CSV files."""
    for code, name in [("en", "english"), ("de", "german")]:
        part = df[df["language"] == code]
        path = f"data/{prefix}_{name}_{date.today().isoformat()}.csv"
        part.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  {name.capitalize()} section: {len(part)} jobs -> {path}")


def main() -> None:
    all_jobs = fetch_all()
    visa_slugs = {job.get("slug") for job in fetch_all(visa_only=True)}

    rows = [to_row(job, visa_slugs) for job in all_jobs if is_data_job(job.get("title"))]
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit(f"Checked {len(all_jobs)} jobs but none had a data-related title.")
    df = df.drop_duplicates(subset="job_id")

    os.makedirs("data", exist_ok=True)
    out_path = f"data/arbeitnow_raw_{date.today().isoformat()}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")  # utf-8-sig so Excel shows ä, ö, ü correctly

    print(f"\nChecked {len(all_jobs)} jobs, kept {len(df)} data-related ones -> {out_path}")
    save_language_files(df, "arbeitnow")
    print(f"Average description length: {df['description'].str.len().mean():.0f} characters")
    print("\nPostings per language:")
    print(df["language"].value_counts().to_string())
    print(f"\nOffering visa sponsorship: {df['visa_sponsorship'].sum()} of {len(df)}")
    print("\nFirst 10 jobs:")
    print(df[["title", "company", "location"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
