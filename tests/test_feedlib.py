"""Tests for the automatic NZ holiday feed. Run: python -m unittest discover -s tests -v

verified/nz-public-holidays.csv holds 2026-2027, checked by hand against Employment NZ (2026-10-21).
Every source must reproduce it exactly before the job may publish anything.
"""
import csv
import datetime as dt
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import feedlib  # noqa: E402

VERIFIED = ROOT / "verified" / "nz-public-holidays.csv"
FIXTURE = ROOT / "tests" / "fixtures" / "employment-nz-tables.html"


def verified(year):
    with open(VERIFIED, encoding="utf-8", newline="") as f:
        return {(r["ObservedDate"], r["Region"]) for r in csv.DictReader(f) if r["ObservedDate"].startswith(str(year))}


def keys(rows):
    return {(d, region) for d, region, _ in rows}


class SourceTests(unittest.TestCase):
    def test_python_holidays_matches_verified(self):
        for y in (2026, 2027):
            self.assertEqual(keys(feedlib.from_python_holidays(y)), verified(y), y)

    def test_date_holidays_matches_verified_except_south_canterbury(self):
        data = feedlib.from_date_holidays([2026, 2027])
        for y in (2026, 2027):
            want = {k for k in verified(y) if k[1] != "Canterbury (South)"}
            self.assertEqual(keys(data[y]), want, y)

    def test_official_page_parser(self):
        tables = feedlib.parse_official(FIXTURE.read_text(encoding="utf-8"), today=dt.date(2026, 10, 21))
        self.assertEqual(sorted(tables), [2026, 2027])
        for y in (2026, 2027):
            self.assertEqual(tables[y], verified(y), y)


class CompareTests(unittest.TestCase):
    def test_agreement_has_no_problems(self):
        a = [("2027-10-25", "National", "Labour Day")]
        self.assertEqual(feedlib.compare(a, a, "x", "y"), [])

    def test_difference_is_reported(self):
        a = [("2027-10-25", "National", "Labour Day")]
        b = [("2027-10-26", "National", "Labour Day")]
        problems = feedlib.compare(a, b, "python holidays", "date-holidays")
        self.assertEqual(len(problems), 2)
        self.assertIn("2027-10-25", " ".join(problems))

    def test_south_canterbury_is_not_compared_when_a_source_lacks_it(self):
        a = [("2027-09-27", "Canterbury (South)", "Canterbury (South) Anniversary Day")]
        self.assertEqual(feedlib.compare(a, [], "x", "date-holidays", skip_regions={"Canterbury (South)"}), [])


class FeedFormatTests(unittest.TestCase):
    def test_items_are_nager_shaped_and_named_for_the_flow(self):
        items = feedlib.to_feed(feedlib.from_python_holidays(2027))
        self.assertEqual(len(items), 23)
        for i in items:
            self.assertTrue({"date", "localName", "name", "countryCode", "global", "counties", "types"} <= i.keys())
            if not i["global"]:
                self.assertTrue(i["name"].endswith(" Anniversary Day"), i["name"])
        names = {i["name"] for i in items}
        self.assertIn("Westland Anniversary Day", names)
        self.assertIn("Canterbury (South) Anniversary Day", names)
        self.assertEqual(json.loads(json.dumps(items)), items)

    def test_only_weekdays(self):
        for y in (2026, 2027, 2028, 2029):
            for d, _, _ in feedlib.from_python_holidays(y):
                self.assertLess(dt.date.fromisoformat(d).weekday(), 5, d)


if __name__ == "__main__":
    unittest.main()
