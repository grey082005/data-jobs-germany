"""
Step 1 of the job-market tracker:
fetch data-related job postings from the Adzuna API and save them to a CSV file.

How it works, in plain words:
1. Read your secret API keys from the .env file (so they never end up on GitHub).
2. Ask Adzuna for job postings for each search term, page by page.
3. Keep only the fields we care about and flatten them into a table.
4. Label each posting as German or English.
5. Remove duplicates (the same job can match several search terms).
6. Save the table as a CSV file named with today's date,
   plus one file with only English and one with only German postings.
"""

import os
import re
import time
from datetime import date

import pandas as pd
import requests
from dotenv import load_dotenv

# --- Settings you can change -------------------------------------------------

COUNTRY = "de"  # country code, e.g. "de", "gb", "nl", "fr", "us"
SEARCH_TERMS = ["data analyst", "data scientist", "business analyst"]
PAGES_PER_TERM = 2       # each page = up to 50 jobs; keep it low, the free plan has a monthly call limit
RESULTS_PER_PAGE = 50

# --- Load API keys -----------------------------------------------------------

load_dotenv()
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

# --- Language detection --------------------------------------------------------
# Guess German vs English by counting common little words from each language.

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


def fetch_page(term: str, page: int) -> list[dict]:
    """Ask Adzuna for one page of job postings matching `term`."""
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": term,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()  # stop with a clear error if something went wrong
    return response.json().get("results", [])


def flatten(job: dict, term: str) -> dict:
    """Turn one nested job record from the API into one flat table row."""
    return {
        "job_id": job.get("id"),
        "search_term": term,
        "title": job.get("title"),
        "company": (job.get("company") or {}).get("display_name"),
        "location": (job.get("location") or {}).get("display_name"),
        "category": (job.get("category") or {}).get("label"),
        "contract_type": job.get("contract_type"),   # e.g. permanent / contract
        "contract_time": job.get("contract_time"),   # e.g. full_time / part_time
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_is_predicted": job.get("salary_is_predicted"),  # "1" = estimated by Adzuna
        "created": job.get("created"),
        "description": job.get("description"),       # note: Adzuna only returns a snippet
        "language": detect_language(f"{job.get('title')} {job.get('description')}"),  # "de" / "en"
        "url": job.get("redirect_url"),
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
    if not APP_ID or not APP_KEY:
        raise SystemExit("API keys missing: create a .env file (see .env.example) and add your Adzuna keys.")

    rows = []
    for term in SEARCH_TERMS:
        for page in range(1, PAGES_PER_TERM + 1):
            jobs = fetch_page(term, page)
            print(f"'{term}' page {page}: {len(jobs)} jobs")
            rows.extend(flatten(job, term) for job in jobs)
            if len(jobs) < RESULTS_PER_PAGE:
                break  # no more results for this term
            time.sleep(1)  # be polite to the API

    df = pd.DataFrame(rows).drop_duplicates(subset="job_id")

    os.makedirs("data", exist_ok=True)
    out_path = f"data/jobs_raw_{date.today().isoformat()}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")  # utf-8-sig so Excel shows ä, ö, ü correctly

    print(f"\nSaved {len(df)} unique jobs to {out_path}")
    save_language_files(df, "jobs")
    print(df[["title", "company", "location"]].head(10).to_string(index=False))

    print("\nPostings per language:")
    print(df["language"].value_counts().to_string())


if __name__ == "__main__":
    main()
