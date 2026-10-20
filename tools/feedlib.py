"""Sources, checks and the output format for the NZ holiday feed.

A row is (observed date "yyyy-MM-dd", region, name). Region is "National" or one of the 12 provinces
in the Employment NZ table. Names of regional days are "<region> Anniversary Day", because the
Holiday update flow reads the region from the name.
"""
import datetime as dt
import html as htmllib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

# python holidays subdivision -> our region name
PY_REGIONS = {
    "AUK": "Auckland", "WGN": "Wellington", "NSN": "Nelson", "TKI": "Taranaki", "OTA": "Otago",
    "STL": "Southland", "CAN": "Canterbury", "South Canterbury": "Canterbury (South)", "HKB": "Hawke's Bay",
    "MBH": "Marlborough", "CIT": "Chatham Islands", "WTC": "Westland",
}
COUNTIES = {
    "Auckland": ["NZ-AUK", "NZ-NTL", "NZ-WKO", "NZ-GIS", "NZ-BOP"], "Wellington": ["NZ-WGN", "NZ-MWT"],
    "Nelson": ["NZ-NSN"], "Taranaki": ["NZ-TKI"], "Otago": ["NZ-OTA"], "Southland": ["NZ-STL"],
    "Canterbury (South)": ["NZ-CAN"], "Hawke's Bay": ["NZ-HKB"], "Marlborough": ["NZ-MBH"],
    "Canterbury": ["NZ-CAN"], "Chatham Islands": ["NZ-CIT"], "Westland": ["NZ-WTC"],
}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                      "august", "september", "october", "november", "december"], 1)}


def _weekday(d):
    return d.weekday() < 5


def from_python_holidays(year):
    import holidays  # installed in the job; MIT licence
    national = {d: n for d, n in holidays.NZ(years=year).items()}
    rows = [(d.isoformat(), "National", n.replace(" (observed)", "")) for d, n in sorted(national.items()) if _weekday(d)]
    for sub, region in PY_REGIONS.items():
        for d, n in sorted(holidays.NZ(subdiv=sub, years=year).items()):
            if _weekday(d) and national.get(d) != n:
                rows.append((d.isoformat(), region, f"{region} Anniversary Day"))
    return rows


def from_date_holidays(years):
    out = subprocess.run(["node", str(ROOT / "tools" / "date_holidays.js"), *map(str, years)],
                         capture_output=True, text=True, check=True, cwd=ROOT)
    return {int(y): [tuple(r) for r in rows] for y, rows in json.loads(out.stdout).items()}


def _cells(row):
    return [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[hd][^>]*>([\s\S]*?)</t[hd]>", row)]


def _observed(text, year):
    """'Saturday 2 January or Monday 4 January' -> the last date (the Monday to Friday observed date).

    Only the date we use is checked against its weekday name. The page has had a typo in the other one:
    2027 said "Saturday 25 April" when 25 April 2027 is a Sunday.
    """
    found = re.findall(r"(\w+day)\s+(\d{1,2})\s+(\w+)", text)
    if not found:
        return None
    wd, day, month = found[-1]
    d = dt.date(year, MONTHS[month.lower()], int(day))
    return d if d.strftime("%A").lower() == wd.lower() and _weekday(d) else None


def _table_year(rows, today):
    """The year whose weekdays match every observed date in the table (tables on the page carry no year)."""
    texts = [c[2] for c in rows if len(c) == 3]
    for year in range(today.year - 1, today.year + 6):
        if texts and all(_observed(t, year) for t in texts):
            return year
    return None


def parse_official(page_html, today=None):
    """Employment NZ tables -> {year: {(date, region)}}. Raises ValueError if the page does not parse."""
    today = today or dt.date.today()
    tables = [[_cells(r) for r in re.findall(r"<tr[\s\S]*?</tr>", t)[1:]]
              for t in re.findall(r"<table[\s\S]*?</table>", page_html)]
    if len(tables) < 2:
        raise ValueError("Employment NZ page: fewer than 2 tables")
    result = {}
    for national, provinces in zip(tables[0::2], tables[1::2]):
        year = _table_year(national, today)
        if year is None or _table_year(provinces, today) != year:
            raise ValueError("Employment NZ page: could not work out the year of a table")
        keys = {(_observed(c[2], year).isoformat(), "National") for c in national}
        keys |= {(_observed(c[2], year).isoformat(), c[0]) for c in provinces}
        result[year] = keys
    return result


def compare(a, b, name_a, name_b, skip_regions=()):
    ka = {(d, r) for d, r, _ in a if r not in skip_regions}
    kb = {(d, r) for d, r, _ in b if r not in skip_regions}
    return ([f"{d} {r}: in {name_a}, not in {name_b}" for d, r in sorted(ka - kb)] +
            [f"{d} {r}: in {name_b}, not in {name_a}" for d, r in sorted(kb - ka)])


def to_feed(rows):
    items = []
    for d, region, name in sorted(rows):
        national = region == "National"
        items.append({"date": d, "localName": name, "name": name, "countryCode": "NZ", "global": national,
                      "counties": None if national else COUNTIES[region], "types": ["Public"]})
    return items
