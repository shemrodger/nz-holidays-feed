"""The monthly job's decision: publish only when every check passes."""
import datetime as dt
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import update  # noqa: E402

TODAY = dt.date(2026, 10, 21)
LABOUR = ("2028-10-23", "National", "Labour Day")


def sources(py_rows, dh_rows, official=None, official_error=None):
    def official_fn(today):
        if official_error:
            raise official_error
        return official or {}
    return {"python": lambda y: py_rows.get(y, []), "date_holidays": lambda ys: {y: dh_rows.get(y, []) for y in ys},
            "official": official_fn}


class UpdateTests(unittest.TestCase):
    def run_job(self, src, verified=None):
        with tempfile.TemporaryDirectory() as d:
            result = update.run(pathlib.Path(d), TODAY, src, verified or {})
            files = sorted(str(p.relative_to(d)).replace("\\", "/") for p in pathlib.Path(d).rglob("NZ.json"))
        return result, files

    def test_publishes_four_years_when_sources_agree(self):
        rows = {y: [LABOUR] if y == 2028 else [] for y in range(2026, 2030)}
        result, files = self.run_job(sources(rows, rows))
        self.assertEqual(result["problems"], [])
        self.assertEqual(files, ["2026/NZ.json", "2027/NZ.json", "2028/NZ.json", "2029/NZ.json"])

    def test_refuses_to_publish_when_sources_disagree(self):
        py = {2028: [LABOUR]}
        dh = {2028: [("2028-10-24", "National", "Labour Day")]}
        result, files = self.run_job(sources(py, dh))
        self.assertTrue(result["problems"])
        self.assertEqual(files, [])

    def test_refuses_when_a_verified_year_changes(self):
        rows = {2026: [("2026-10-26", "National", "Labour Day")]}
        result, files = self.run_job(sources(rows, rows), verified={2026: {("2026-10-27", "National")}})
        self.assertTrue(any("verified" in p for p in result["problems"]))
        self.assertEqual(files, [])

    def test_refuses_when_the_official_page_disagrees(self):
        rows = {2027: [("2027-10-25", "National", "Labour Day")]}
        result, files = self.run_job(sources(rows, rows, official={2027: {("2027-10-26", "National")}}))
        self.assertTrue(any("Employment NZ" in p for p in result["problems"]))
        self.assertEqual(files, [])

    def test_unreadable_official_page_is_only_a_warning(self):
        rows = {y: [] for y in range(2026, 2030)}
        result, files = self.run_job(sources(rows, rows, official_error=ValueError("layout changed")))
        self.assertEqual(result["problems"], [])
        self.assertTrue(result["warnings"])
        self.assertEqual(len(files), 4)


if __name__ == "__main__":
    unittest.main()
