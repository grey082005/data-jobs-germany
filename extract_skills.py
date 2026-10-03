"""
Step 2 of the job-market tracker: find out which skills employers ask for.

How it works, in plain words:
1. Load the newest Arbeitnow file from the data folder (it has full descriptions).
2. Sort every job into a role (Data Analyst, Data Scientist, ...) and a level
   (Intern / Working student, Junior, Senior, ...) based on its title.
3. Search each description for ~40 skills, in English AND German spellings
   (e.g. "statistics" / "Statistik").
4. Count how often each skill appears, overall and for English vs German postings.
5. Save two files: every job with its skills, and the skill ranking.
"""

import glob
import re
from datetime import date

import pandas as pd

# --- Skills to look for ----------------------------------------------------------
# Each skill has a list of search patterns. \b means "word boundary", so "sql"
# matches "SQL" but not "postgresql" (that one gets its own pattern below).

SKILLS = {
    # Languages & querying
    "SQL": [r"\bsql\b", r"postgres", r"mysql", r"t-sql", r"pl/sql"],
    "Python": [r"\bpython\b", r"\bpandas\b", r"\bnumpy\b"],
    "R": [],  # handled separately below, because a single letter needs special care
    "Excel": [r"\bexcel\b", r"spreadsheet", r"vba"],
    "Scala": [r"\bscala\b"],
    "Java": [r"\bjava\b"],
    # BI & visualisation
    "Power BI": [r"power ?bi", r"\bdax\b"],
    "Tableau": [r"\btableau\b"],
    "Looker": [r"\blooker\b"],
    "Qlik": [r"\bqlik"],
    "Data visualisation": [r"visuali[sz]ation", r"dashboards?", r"visualisierung"],
    # Data engineering & cloud
    "Spark": [r"\bspark\b", r"pyspark", r"databricks"],
    "Airflow": [r"\bairflow\b"],
    "dbt": [r"\bdbt\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "BigQuery": [r"bigquery"],
    "ETL / data pipelines": [r"\betl\b", r"\belt\b", r"data pipelines?", r"datenpipelines?"],
    "Data modelling": [r"data model(l)?ing", r"datenmodellierung", r"data warehous", r"datawarehouse"],
    "AWS": [r"\baws\b", r"amazon web services"],
    "Azure": [r"\bazure\b"],
    "Google Cloud": [r"\bgcp\b", r"google cloud"],
    "Docker / Kubernetes": [r"\bdocker\b", r"kubernetes", r"\bk8s\b"],
    "Git": [r"\bgit\b", r"github", r"gitlab"],
    "SAP": [r"\bsap\b"],
    # Analysis & data science
    "Statistics": [r"statistic", r"statistik"],
    "Machine learning": [r"machine learning", r"maschinelles lernen", r"\bml\b"],
    "Deep learning": [r"deep learning", r"neural network", r"neuronale"],
    "AI / LLMs": [r"\bllms?\b", r"generative ai", r"\bgenai\b", r"künstliche intelligenz", r"\bki\b"],
    "scikit-learn": [r"scikit", r"sklearn"],
    "TensorFlow / PyTorch": [r"tensorflow", r"pytorch"],
    "A/B testing": [r"a/b[- ]test", r"experimentation", r"experiment design"],
    "Forecasting": [r"forecast", r"prognose", r"time series", r"zeitreihen"],
    "Data quality / governance": [r"data quality", r"datenqualität", r"data governance"],
    "Google Analytics": [r"google analytics", r"\bga4\b"],
    # Ways of working
    "Agile / Scrum": [r"\bagile\b", r"\bscrum\b", r"agil\b", r"agilen"],
    "Communication / storytelling": [r"communication skills", r"storytelling", r"kommunikationsstärke", r"kommunikationsfähigkeit"],
    "Stakeholder management": [r"stakeholder"],
    # Language requirements
    "German required": [r"fluent (in )?german", r"german \(?c1", r"german \(?c2", r"german language",
                        r"deutschkenntnisse", r"fließend(e|es)? deutsch", r"verhandlungssicher(e|es)? deutsch",
                        r"sehr gute(n)? deutsch"],
    "English required": [r"fluent (in )?english", r"english \(?c1", r"englischkenntnisse",
                         r"fließend(e|es)? englisch", r"verhandlungssicher(e|es)? englisch",
                         r"sehr gute(n)? englisch"],
}

# "R" as a programming language: a capital R standing on its own, e.g. "Python, R or SQL"
R_PATTERN = re.compile(r"(?<![\w/&-])R(?![\w&'’/-])(?=\s*(,|/|\bor\b|\boder\b|\band\b|\bund\b|\)|[Ss]tudio|$))")


def find_skills(text: str) -> dict:
    """Return {skill: True/False} for one job description."""
    lower = text.lower()
    found = {skill: any(re.search(p, lower) for p in patterns) for skill, patterns in SKILLS.items()}
    found["R"] = bool(R_PATTERN.search(text)) or "rstudio" in lower
    return found


# --- Role and level from the job title ---------------------------------------------

def job_role(title: str) -> str:
    t = title.lower()
    if re.search(r"scien|machine learning|\bml\b|\bai\b|\bki\b", t):
        return "Data Scientist / ML"
    if re.search(r"data engineer|analytics engineer|data platform|etl|data architect", t):
        return "Data Engineer"
    if re.search(r"\bbi\b|business intelligence|reporting|power bi", t):
        return "BI / Reporting"
    if re.search(r"business analyst|business analy", t):
        return "Business Analyst"
    if re.search(r"analyst|analytics|analyse|insights|controll", t):
        return "Data Analyst"
    return "Other (title mentions data)"   # e.g. "Backend Engineer - Data Core"


def job_level(title: str) -> str:
    t = title.lower()
    if re.search(r"intern\b|internship|praktik|werkstudent|working student|thesis|abschlussarbeit", t):
        return "Intern / Working student"
    if re.search(r"junior|\bjr\b|entry|graduate|trainee|einsteiger", t):
        return "Junior"
    if re.search(r"senior|\bsr\b|lead|principal|head|staff|manager", t):
        return "Senior / Lead"
    return "Mid / not stated"


# --- Main ------------------------------------------------------------------------

def newest_file(pattern: str) -> str:
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No file matching {pattern} found. Run fetch_arbeitnow.py first.")
    return files[-1]


def main() -> None:
    in_path = newest_file("data/arbeitnow_raw_*.csv")
    jobs = pd.read_csv(in_path, encoding="utf-8-sig")
    print(f"Loaded {len(jobs)} jobs from {in_path}")

    jobs["role"] = jobs["title"].fillna("").apply(job_role)
    jobs["level"] = jobs["title"].fillna("").apply(job_level)

    skill_table = jobs["description"].fillna("").apply(find_skills).apply(pd.Series)
    jobs = pd.concat([jobs, skill_table], axis=1)

    # Keep real data roles only (drop software jobs that just mention "data" in the title)
    data_jobs = jobs[jobs["role"] != "Other (title mentions data)"]
    print(f"Real data roles: {len(data_jobs)} (removed {len(jobs) - len(data_jobs)} software jobs with 'data' in the title)")

    skills = list(skill_table.columns)
    english = data_jobs[data_jobs["language"] == "en"]
    german = data_jobs[data_jobs["language"] == "de"]

    ranking = pd.DataFrame({
        "skill": skills,
        "jobs_mentioning": [int(data_jobs[s].sum()) for s in skills],
        "share_all_%": [round(100 * data_jobs[s].mean(), 1) for s in skills],
        "share_english_postings_%": [round(100 * english[s].mean(), 1) if len(english) else None for s in skills],
        "share_german_postings_%": [round(100 * german[s].mean(), 1) if len(german) else None for s in skills],
    }).sort_values("jobs_mentioning", ascending=False)

    today = date.today().isoformat()
    jobs.to_csv(f"data/jobs_with_skills_{today}.csv", index=False, encoding="utf-8-sig")
    ranking.to_csv(f"data/skill_ranking_{today}.csv", index=False, encoding="utf-8-sig")

    print("\nJobs per role:")
    print(data_jobs["role"].value_counts().to_string())
    print("\nJobs per level:")
    print(data_jobs["level"].value_counts().to_string())
    print(f"\nTop 20 skills ({len(english)} English and {len(german)} German postings):")
    print(ranking.head(20).to_string(index=False))
    print(f"\nSaved data/jobs_with_skills_{today}.csv and data/skill_ranking_{today}.csv")


if __name__ == "__main__":
    main()
