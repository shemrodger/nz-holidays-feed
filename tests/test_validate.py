"""The publish step's sanity check. It uses only the Python standard library, because the publish
step holds write access and must not run third-party package code."""
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import feedlib  # noqa: E402
import update  # noqa: E402
import validate_feed  # noqa: E402


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        src = {"python": feedlib.from_python_holidays,
               "date_holidays": lambda ys: {y: feedlib.from_python_holidays(y) for y in ys},
               "official": lambda today: {}}
        result = update.run(self.root, dt.date(2026, 10, 21), src, {})
        self.assertEqual(result["problems"], [])

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, year, change):
        path = self.root / str(year) / "NZ.json"
        items = json.loads(path.read_text(encoding="utf-8"))
        change(items)
        path.write_text(json.dumps(items), encoding="utf-8", newline="\n")

    def test_good_feed_passes(self):
        self.assertEqual(validate_feed.validate(self.root), [])

    def test_years_index(self):
        index = json.loads((self.root / "years.json").read_text(encoding="utf-8"))
        self.assertEqual(index["years"], [2026, 2027, 2028, 2029])
        self.assertEqual(index["latest"], 2029)
        self.assertEqual(index["updated"], "2026-10-21")
        self.assertEqual(index["url"], "https://shemrodger.github.io/nz-holidays-feed/{year}/NZ.json")

    def test_date_in_the_wrong_year(self):
        self.edit(2027, lambda items: items[0].update(date="2028-01-03"))
        self.assertTrue(any("2027" in p and "year" in p for p in validate_feed.validate(self.root)))

    def test_weekend_date(self):
        self.edit(2027, lambda items: items[0].update(date="2027-01-02"))  # a Saturday
        self.assertTrue(any("weekend" in p for p in validate_feed.validate(self.root)))

    def test_missing_field(self):
        self.edit(2027, lambda items: items[0].pop("global"))
        self.assertTrue(any("field" in p for p in validate_feed.validate(self.root)))

    def test_too_few_holidays(self):
        self.edit(2027, lambda items: items.__delitem__(slice(5, None)))
        self.assertTrue(any("count" in p for p in validate_feed.validate(self.root)))

    def test_index_must_match_the_files(self):
        shutil.rmtree(self.root / "2029")
        self.assertTrue(any("years.json" in p for p in validate_feed.validate(self.root)))

    def test_regional_names_must_end_with_anniversary_day(self):
        self.edit(2027, lambda items: next(i for i in items if not i["global"]).update(name="Show Day"))
        self.assertTrue(any("Anniversary Day" in p for p in validate_feed.validate(self.root)))



class PublishStepIsolationTests(unittest.TestCase):
    def test_validator_imports_only_the_standard_library(self):
        import ast
        tree = ast.parse((ROOT / "tools" / "validate_feed.py").read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertTrue(names <= set(sys.stdlib_module_names), names - set(sys.stdlib_module_names))


if __name__ == "__main__":
    unittest.main()
