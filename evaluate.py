"""
Evaluation, part 2: score the skill detection against your hand labels.

How it works, in plain words:
1. Read your labels (labelling/labels.csv) and find the full text of those 50 ads
   in the Arbeitnow files in data/.
2. Run the keyword rules from extract_skills.py on each ad.
3. Compare, skill by skill, what the rules said with what you said:
   - true positive  (TP): both say "asks for it"
   - false positive (FP): the rules say yes, you said no   -> the rules over-count
   - false negative (FN): you said yes, the rules said no  -> the rules miss it
4. Turn those counts into three scores:
   - precision = TP / (TP + FP): when the rules say "yes", how often are they right?
   - recall    = TP / (TP + FN): of all real mentions, how many did the rules find?
   - F1        = the balance of the two (harmonic mean), one number per skill
5. If labelling/predictions_<name>.csv files exist (for example from an AI model),
   score those too, so all methods are compared on exactly the same ads.
6. Save the scores to labelling/scores.csv and every disagreement, with the sentence
   that caused it, to labelling/disagreements.csv.
"""

import glob
import os
import re

import pandas as pd

from extract_skills import R_PATTERN, SKILLS, find_skills
from make_label_tool import LABEL_SKILLS

DIR = "labelling"


def load_ads(job_ids: set) -> pd.DataFrame:
    """Find the full text of the labelled ads in any Arbeitnow file."""
    frames = [pd.read_csv(f, encoding="utf-8-sig") for f in sorted(glob.glob("data/arbeitnow_raw_*.csv"), reverse=True)]
    if not frames:
        raise SystemExit("No Arbeitnow files in data/. The ad texts are needed to run the rules.")
    ads = pd.concat(frames).drop_duplicates(subset="job_id")
    ads = ads[ads["job_id"].isin(job_ids)]
    missing = job_ids - set(ads["job_id"])
    if missing:
        print(f"Warning: {len(missing)} labelled ads not found in data/ and skipped.")
    return ads.set_index("job_id")


def evidence(skill: str, text: str) -> str:
    """The words around the first keyword match, so you can see why the rules said yes."""
    if skill == "R":
        m = R_PATTERN.search(text)
    else:
        m = next((m for p in SKILLS[skill] if (m := re.search(p, text.lower()))), None)
    if not m:
        return ""
    a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def score(truth: pd.DataFrame, pred: pd.DataFrame, method: str, languages: pd.Series) -> pd.DataFrame:
    rows = []
    for group, mask in [("all", languages.notna()), ("English ads", languages == "en"), ("German ads", languages == "de")]:
        t, p = truth[mask], pred[mask]
        for skill in LABEL_SKILLS + ["ALL SKILLS"]:
            tt = t.values.ravel() if skill == "ALL SKILLS" else t[skill].values
            pp = p.values.ravel() if skill == "ALL SKILLS" else p[skill].values
            tp = int(((tt == 1) & (pp == 1)).sum())
            fp = int(((tt == 0) & (pp == 1)).sum())
            fn = int(((tt == 1) & (pp == 0)).sum())
            prec = tp / (tp + fp) if tp + fp else None
            rec = tp / (tp + fn) if tp + fn else None
            f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if tp + fp + fn else None)
            rows.append({"method": method, "ads": group, "skill": skill, "real_mentions": tp + fn,
                         "TP": tp, "FP": fp, "FN": fn,
                         "precision": round(prec, 2) if prec is not None else None,
                         "recall": round(rec, 2) if rec is not None else None,
                         "F1": round(f1, 2) if f1 is not None else None})
    return pd.DataFrame(rows)


def main() -> None:
    path = f"{DIR}/labels.csv"
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found. Label the ads in label_tool.html and save labels.csv there.")
    labels = pd.read_csv(path, encoding="utf-8-sig").set_index("job_id")
    ads = load_ads(set(labels.index))
    labels = labels.loc[labels.index.intersection(ads.index)]
    truth = labels[LABEL_SKILLS].astype(int)
    languages = labels["language"]

    methods = {"rules": pd.DataFrame(
        [{s: int(find_skills(str(ads.at[j, "description"]))[s]) for s in LABEL_SKILLS} for j in truth.index],
        index=truth.index)}
    for f in sorted(glob.glob(f"{DIR}/predictions_*.csv")):
        name = os.path.basename(f)[len("predictions_"):-4]
        p = pd.read_csv(f, encoding="utf-8-sig").set_index("job_id").reindex(truth.index)
        methods[name] = p[LABEL_SKILLS].fillna(0).astype(int)

    scores = pd.concat([score(truth, pred, name, languages) for name, pred in methods.items()])
    scores.to_csv(f"{DIR}/scores.csv", index=False, encoding="utf-8-sig")

    # Every disagreement between you and the rules, with the reason where there is one
    rules = methods["rules"]
    rows = []
    for j in truth.index:
        text = str(ads.at[j, "description"])
        for s in LABEL_SKILLS:
            if truth.at[j, s] != rules.at[j, s]:
                rows.append({"job_id": j, "language": languages[j], "title": ads.at[j, "title"], "skill": s,
                             "you": truth.at[j, s], "rules": rules.at[j, s],
                             "type": "false positive (rules over-count)" if rules.at[j, s] else "false negative (rules miss it)",
                             "evidence": evidence(s, text) if rules.at[j, s] else "",
                             "your_note": labels.at[j, "note"] if "note" in labels else ""})
    pd.DataFrame(rows).to_csv(f"{DIR}/disagreements.csv", index=False, encoding="utf-8-sig")

    print(f"Scored {len(truth)} ads ({(languages == 'en').sum()} English, {(languages == 'de').sum()} German)\n")
    overall = scores[(scores["ads"] == "all")]
    print(overall[overall["skill"] == "ALL SKILLS"][["method", "precision", "recall", "F1"]].to_string(index=False))
    print("\nRules, per skill:")
    view = overall[(overall["method"] == "rules") & (overall["skill"] != "ALL SKILLS")]
    print(view[["skill", "real_mentions", "TP", "FP", "FN", "precision", "recall", "F1"]].to_string(index=False))
    by_lang = scores[(scores["skill"] == "ALL SKILLS") & (scores["ads"] != "all")]
    print("\nBy language of the ad:")
    print(by_lang[["method", "ads", "precision", "recall", "F1"]].to_string(index=False))
    print(f"\nSaved {DIR}/scores.csv and {DIR}/disagreements.csv ({len(rows)} disagreements to read through).")


if __name__ == "__main__":
    main()
