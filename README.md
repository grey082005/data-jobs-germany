# Data Jobs in Germany

**What do data jobs in Germany actually ask for, and how open are they to international graduates?**

A weekly, automated tracker of data analyst, data scientist, data engineer and BI job postings in Germany. It collects postings from two job APIs, finds about 40 skills in English and German text, and compares English-language postings with German-language ones. The comparison tells international applicants a lot: which jobs need German, which skills each kind of employer wants, and how many roles are open at entry level.

**[View the interactive dashboard](https://claude.ai/artifact/2QBbehWbNZV9rxpTpNo6sf)**

![Dashboard: top skills, language requirements, roles and seniority in German data job postings](docs/dashboard.png)

## Key findings (first snapshot, 3 Oct 2026, 173 data roles)

| Finding | Number |
|---|---|
| German required in **German-language** postings | **67%** |
| German required in **English-language** postings | **3%** |
| Postings that ask for Python / SQL | 49% / 46% |
| Entry-level roles (internship, working student, junior) | 11% (19 of 173) |
| Data jobs offering visa sponsorship | 12% (25 of 209) |

1. **The language of a posting tells you whether you need German.** If a job is advertised in English, it almost never requires German.
2. **Python and SQL are the baseline** in both kinds of postings, at almost the same rate.
3. **The two kinds of employers want different things.** English postings ask more often for A/B testing (+28 percentage points), machine learning (+24), stakeholder management (+24) and statistics (+18). German postings ask more often for AI/LLMs (+27), Azure (+21) and data modelling (+14).
4. **Entry-level roles are scarce.** Half of all postings are senior or lead roles; working-student roles are the main way in.

## How it works

```
Arbeitnow API ──┐                                        ┌─> history/skill_history.csv
 (full text)    ├─> fetch ─> language ─> skills, role ───┤
Adzuna API ─────┘            (de / en)    and level      └─> history/market_history.csv
 (counts, salaries)                                               │
                                                                  └─> dashboard and charts
```

| Step | Script | What it does |
|---|---|---|
| 1 | `fetch_arbeitnow.py` | Collects postings with full descriptions from the [Arbeitnow API](https://www.arbeitnow.com/blog/job-board-api), keeps data roles, marks visa sponsorship |
| 1b | `fetch_jobs.py` | Collects postings from the [Adzuna API](https://developer.adzuna.com/) for job counts, locations and salaries |
| 2 | `extract_skills.py` | Finds ~40 skills with English and German patterns (e.g. *statistics* / *Statistik*), sorts each job into a role and a seniority level |
| 3 | `update_history.py` | Appends this week's summary numbers to the history files |
| 4 | `make_charts.py` | Draws the skill comparison chart |
| all | `pipeline.py` | Runs steps 1 to 3 in order |

**Automation:** a GitHub Actions workflow (`.github/workflows/weekly.yml`) runs the pipeline every Monday and commits the new numbers to `history/`. Only summary numbers are stored in the repository, never the job ads themselves.

## Data decisions and limitations

- **Why two sources:** Adzuna's API returns only the first 500 characters of each description, which is usually the company introduction. In the first Adzuna sample, SQL appeared in only 3 of 297 postings. Arbeitnow returns full descriptions (about 5,000 characters on average), so skills are counted from Arbeitnow and Adzuna is used for market size.
- **Coverage:** Arbeitnow leans towards tech companies and startups that use applicant tracking systems such as Greenhouse. It is not the whole German market.
- **Language detection** counts common German and English words. It labelled all but 5 of 507 postings in the first run; those are marked *unknown*.
- **Skill matching** is rule-based, so it only finds skills on the list. The next step tests it against an LLM and against hand-labelled postings.
- **Duplicates:** some companies repost the same job under a new ID.

## Roadmap

- [x] Two data sources, language detection, bilingual skill extraction
- [x] Interactive dashboard
- [x] Weekly automated collection with history
- [ ] Trends over time once there are 4+ weekly snapshots
- [ ] LLM skill extraction, evaluated against rule-based matching on 50 hand-labelled postings (precision, recall, F1)
- [ ] Model which factors predict entry-level access and visa sponsorship
- [ ] Skill-gap tool: compare a CV with current demand

## Run it yourself

```bash
pip install -r requirements.txt
python pipeline.py
```

Adzuna is optional and needs a free key from [developer.adzuna.com](https://developer.adzuna.com/). Copy `.env.example` to `.env` and add the key. Without it the pipeline skips Adzuna and still runs.

Built with Python (pandas, requests, regular expressions, matplotlib) and GitHub Actions.
