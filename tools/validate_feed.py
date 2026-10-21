"""Sanity check for the published feed. Standard library only.

    python tools/validate_feed.py [folder]     exit 0 = publish, exit 1 = refuse

The publish step runs this with write access to the repo, so it must never import third-party
packages. It checks the shape of the data, not where it came from: the build step does that.
"""
import datetime as dt
import json
import pathlib
import sys

FIELDS = {"date", "localName", "name", "countryCode", "global", "counties", "types"}
MIN_COUNT, MAX_COUNT = 18, 30  # NZ has 11 national days and 12 regional ones today


def validate(root):
    root = pathlib.Path(root)
    problems = []
    years = sorted(int(p.parent.name) for p in root.glob("*/NZ.json") if p.parent.name.isdigit())
    if not years:
        return ["no {year}/NZ.json files found"]
    for y in years:
        path = root / str(y) / "NZ.json"
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{y}: not valid JSON ({e})")
            continue
        if not isinstance(items, list):
            problems.append(f"{y}: not a list")
            continue
        if not MIN_COUNT <= len(items) <= MAX_COUNT:
            problems.append(f"{y}: count {len(items)} is outside {MIN_COUNT}-{MAX_COUNT}")
        seen = set()
        for i, item in enumerate(items):
            missing = FIELDS - set(item) if isinstance(item, dict) else FIELDS
            if missing:
                problems.append(f"{y} item {i}: missing field(s) {sorted(missing)}")
                continue
            try:
                d = dt.date.fromisoformat(item["date"])
            except (TypeError, ValueError):
                problems.append(f"{y} item {i}: bad date {item['date']!r}")
                continue
            if d.year != y:
                problems.append(f"{y} item {i}: {item['date']} is not in year {y}")
            if d.weekday() >= 5:
                problems.append(f"{y} item {i}: {item['date']} falls on a weekend")
            if not isinstance(item["global"], bool) or item["countryCode"] != "NZ":
                problems.append(f"{y} item {i}: bad global or countryCode")
            if not item["global"] and not str(item["name"]).endswith(" Anniversary Day"):
                problems.append(f"{y} item {i}: regional name {item['name']!r} must end with ' Anniversary Day'")
            key = (item["date"], item["name"])
            if key in seen:
                problems.append(f"{y} item {i}: duplicate {key}")
            seen.add(key)
    try:
        index = json.loads((root / "years.json").read_text(encoding="utf-8"))
        if index.get("years") != years or index.get("latest") != years[-1]:
            problems.append(f"years.json lists {index.get('years')}, but the files are {years}")
    except (OSError, ValueError) as e:
        problems.append(f"years.json is missing or not valid JSON ({e})")
    return problems


if __name__ == "__main__":
    found = validate(sys.argv[1] if len(sys.argv) > 1 else ".")
    for p in found:
        print("PROBLEM:", p)
    sys.exit(1 if found else 0)
