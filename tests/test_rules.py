"""Quick checks that the text rules behave as intended. Run with:  python -m pytest"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extract_skills import find_skills, job_level, job_role  # noqa: E402
from fetch_arbeitnow import detect_language, html_to_text, is_data_job  # noqa: E402


# --- Language detection ---------------------------------------------------------

def test_detects_german():
    assert detect_language("Wir suchen dich mit Kenntnissen in SQL und Python für unser Team") == "de"


def test_detects_english():
    assert detect_language("We are looking for someone with SQL and Python skills to join our team") == "en"


def test_empty_text_is_unknown():
    assert detect_language("") == "unknown"
    assert detect_language(None) == "unknown"


# --- Skill matching ---------------------------------------------------------------

def test_finds_skills_in_both_languages():
    en = find_skills("Strong SQL, Python and statistics skills; dashboards in Power BI.")
    de = find_skills("Sehr gute Kenntnisse in SQL, Statistik und maschinelles Lernen.")
    assert en["SQL"] and en["Python"] and en["Statistics"] and en["Power BI"] and en["Data visualisation"]
    assert de["SQL"] and de["Statistics"] and de["Machine learning"]


def test_word_boundaries():
    assert not find_skills("We use PostgreSQL and Snowflake")["Java"]
    assert not find_skills("JavaScript developer")["Java"]


def test_r_language_without_false_alarms():
    assert find_skills("Experience with Python, R or SQL")["R"]
    assert find_skills("Kenntnisse in R und Python")["R"]
    assert not find_skills("Join our R&D team")["R"]
    assert not find_skills("Contact Mr R. Smith")["R"]


def test_german_requirement():
    assert find_skills("Fluent German (C1) is required")["German required"]
    assert find_skills("Fließende Deutschkenntnisse in Wort und Schrift")["German required"]
    assert not find_skills("Our team in Germany works in English")["German required"]


# --- Roles and levels ---------------------------------------------------------------

def test_roles():
    assert job_role("Senior Data Scientist (m/w/d)") == "Data Scientist / ML"
    assert job_role("Analytics Engineer") == "Data Engineer"
    assert job_role("BI Developer") == "BI / Reporting"
    assert job_role("Junior Data Analyst") == "Data Analyst"
    assert job_role("Senior Backend Engineer - Data Core") == "Other (title mentions data)"


def test_levels():
    assert job_level("Werkstudent*in Data Analytics (m/w/d)") == "Intern / Working student"
    assert job_level("Praktikant Data Analyst") == "Intern / Working student"
    assert job_level("Junior BI Developer") == "Junior"
    assert job_level("Lead Data Engineer") == "Senior / Lead"
    assert job_level("Data Analyst") == "Mid / not stated"


# --- Cleaning -------------------------------------------------------------------------

def test_html_to_text():
    assert html_to_text("<p>SQL &amp; <b>Python</b></p>\n<ul><li>dbt</li></ul>") == "SQL & Python dbt"


def test_data_title_filter():
    assert is_data_job("Data Analyst (m/w/d)")
    assert is_data_job("BI Consultant")
    assert not is_data_job("Frontend Developer")
