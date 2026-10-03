"""
The whole job-market tracker in one command:  python pipeline.py

Runs every step in order:
1. Fetch jobs from Arbeitnow (full descriptions)
2. Fetch jobs from Adzuna (job counts, salaries) - skipped if no API keys are set
3. Find the skills in every posting
4. Add this run's numbers to the history files

GitHub runs this file automatically every Monday (see .github/workflows/weekly.yml).
"""

import extract_skills
import fetch_arbeitnow
import fetch_jobs
import update_history


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    step("1/4 Fetching Arbeitnow jobs")
    fetch_arbeitnow.main()

    step("2/4 Fetching Adzuna jobs")
    try:
        fetch_jobs.main()
    except (SystemExit, Exception) as reason:   # e.g. no API keys or Adzuna is down: carry on without it
        print(f"Skipped Adzuna: {reason}")

    step("3/4 Finding skills")
    extract_skills.main()

    step("4/4 Updating history")
    update_history.main()


if __name__ == "__main__":
    main()
