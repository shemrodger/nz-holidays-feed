"""Monthly job: rebuild this year and the next 3 years, and publish only if every check passes.

    python tools/update.py            (run by .github/workflows/update.yml)

Checks, all must pass before any file is written:
1. Python `holidays` and `date-holidays` agree (South Canterbury is checked by the other checks only:
   date-holidays has no South Canterbury day).
2. Years in verified/nz-public-holidays.csv are reproduced exactly.
3. Years shown on the Employment NZ page are reproduced exactly. If the page cannot be read, that is a
   warning, not a failure, so a website change cannot stop the feed.
On failure it writes report.md (the job turns it into a GitHub issue) and exits 1.
"""
import csv
import datetime as dt
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import feedlib  # noqa: E402

OFFICIAL_URL = "https://employment.govt.nz/leave-and-holidays/public-holidays/public-holidays-and-anniversary-dates"
YEARS_AHEAD = 3
FEED_URL = "https://shemrodger.github.io/nz-holidays-feed/{year}/NZ.json"

README = """# NZ public holidays feed

New Zealand public holidays and regional anniversary days, one JSON file per year, at `{{year}}/NZ.json`.
For example: `https://shemrodger.github.io/nz-holidays-feed/2027/NZ.json`.
`years.json` lists the years in the feed and the latest one.

- Dates are the observed (Mondayised) dates for a Monday to Friday worker.
- The format matches the Nager.Date API: `date`, `localName`, `name`, `countryCode`, `global`, `counties`, `types`.
- Use the English `name` to tell the two Canterbury days apart: both carry the code NZ-CAN.

## How it stays current
A GitHub Actions job runs on the 1st of each month. It rebuilds this year and the next {ahead} years from two
open-source packages (Python `holidays` and `date-holidays`), and publishes only when:
1. both packages agree,
2. the years we checked by hand (`verified/`) come out exactly the same, and
3. every year shown on the Employment NZ page comes out exactly the same:
   {url}

If a check fails, nothing is published and the job opens a GitHub issue.

Years in this feed: {years}. Last checked: {checked}.

No warranty. Employment NZ notes that regional dates can contain errors. Check them with the local council.
"""


def load_verified(path=ROOT / "verified" / "nz-public-holidays.csv"):
    out = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(int(r["ObservedDate"][:4]), set()).add((r["ObservedDate"], r["Region"]))
    return out


def fetch_official(today):
    req = urllib.request.Request(OFFICIAL_URL, headers={"User-Agent": "nz-holidays-feed monthly check"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return feedlib.parse_official(resp.read().decode("utf-8", "replace"), today=today)


DEFAULT_SOURCES = {"python": feedlib.from_python_holidays, "date_holidays": feedlib.from_date_holidays,
                   "official": fetch_official}


def run(out_dir, today, sources, verified):
    years = list(range(today.year, today.year + YEARS_AHEAD + 1))
    problems, warnings = [], []
    py = {y: sources["python"](y) for y in years}
    dh = sources["date_holidays"](years)
    for y in years:
        problems += [f"{y} packages: {p}" for p in feedlib.compare(py[y], dh.get(y, []), "python holidays", "date-holidays",
                                                                    skip_regions={"Canterbury (South)"})]
        if y in verified:
            got = {(d, r) for d, r, _ in py[y]}
            problems += [f"{y} verified: {d} {r} missing" for d, r in sorted(verified[y] - got)]
            problems += [f"{y} verified: {d} {r} not expected" for d, r in sorted(got - verified[y])]
    try:
        official = sources["official"](today)
        for y, keys in sorted(official.items()):
            if y in py:
                got = {(d, r) for d, r, _ in py[y]}
                problems += [f"{y} Employment NZ: {d} {r} missing" for d, r in sorted(keys - got)]
                problems += [f"{y} Employment NZ: {d} {r} not on the page" for d, r in sorted(got - keys)]
    except Exception as e:  # network or layout change: warn, do not block the feed
        warnings.append(f"Employment NZ page could not be checked: {e}")
    if not problems:
        for y in years:
            path = pathlib.Path(out_dir) / str(y) / "NZ.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(feedlib.to_feed(py[y]), indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")  # same bytes on Windows and Linux
        published = sorted(int(p.parent.name) for p in pathlib.Path(out_dir).glob("*/NZ.json"))
        index = {"country": "NZ", "years": published, "latest": published[-1], "updated": today.isoformat(),
                 "url": FEED_URL}
        (pathlib.Path(out_dir) / "years.json").write_text(json.dumps(index, indent=2) + "\n",
                                                          encoding="utf-8", newline="\n")
        (pathlib.Path(out_dir) / "README.md").write_text(README.format(
            ahead=YEARS_AHEAD, url=OFFICIAL_URL, years=", ".join(map(str, published)), checked=today.isoformat()),
            encoding="utf-8", newline="\n")
    return {"years": years, "problems": problems, "warnings": warnings}


def main():
    result = run(ROOT, dt.date.today(), DEFAULT_SOURCES, load_verified())
    for w in result["warnings"]:
        print("WARNING:", w)
    if result["problems"]:
        report = ["# Holiday feed check failed", "", "Nothing was published. These checks failed:", ""]
        report += [f"- {p}" for p in result["problems"]]
        report += ["", "Fix the cause, then run the job again from the Actions tab."]
        (ROOT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print("\n".join(report))
        sys.exit(1)
    print("Published years:", ", ".join(map(str, result["years"])))


if __name__ == "__main__":
    main()
