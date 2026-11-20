import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from app import SyncshellAnalyzer, _ZIP_UID_CACHE


class OnlineAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        _ZIP_UID_CACHE.clear()
        self.addCleanup(_ZIP_UID_CACHE.clear)

    def report(self, character, entries):
        name = f"lightless_diagnostics_2026-11-21_10-00-{character}.zip"
        with zipfile.ZipFile(self.folder / name, "w") as archive:
            archive.writestr("lightless_diagnostics_report.json", json.dumps({"uid": character}))
            for uid, status, groups in entries:
                status_line = f"Online: {status}\n" if status is not None else ""
                memberships = "\n".join(f"Group {gid} [{gid}]" for gid in groups)
                archive.writestr(
                    f"pairs/not-visible/{uid}.txt",
                    f"Pair\n{status_line}\nSyncshell Memberships\n{memberships}\n",
                )

    def analyze(self, character):
        with contextlib.redirect_stdout(io.StringIO()):
            return SyncshellAnalyzer(str(self.folder)).analyze(character)

    def test_online_snapshot_and_full_leave_impact(self):
        self.report("01", [
            ("SHARED", "Yes", ("A", "B")),
            ("OFFLINE", "No", ("A", "B")),
            ("ONLINE", "True", ("A",)),
            ("UNKNOWN", None, ("A",)),
            ("ONLYOFFLINE", "False", ("C",)),
        ])
        data = self.analyze("01")
        groups = {group["gid"]: group for group in data["groups"]}
        self.assertEqual(groups["A"]["total_members"], 4)
        self.assertEqual(groups["A"]["unique_members_count"], 2)
        self.assertEqual(groups["A"]["online"]["total_members"], 2)
        self.assertEqual(groups["A"]["online"]["unknown_members_count"], 1)
        self.assertEqual(groups["A"]["online"]["unique_members"], ["ONLINE"])
        self.assertEqual(groups["A"]["online"]["overlaps"], {"B": 1})
        self.assertEqual(groups["A"]["online"]["redundancy_pct"], 50.0)
        self.assertEqual(groups["C"]["online"]["total_members"], 0)
        self.assertIsNone(groups["C"]["online"]["redundancy_pct"])
        self.assertEqual(groups["C"]["leave_impact"], "Low")
        self.assertEqual(data["summary"]["online"]["total_unique_players"], 2)
        self.assertEqual(data["summary"]["online"]["average_redundancy_pct"], 75.0)

    def test_unknown_and_all_offline_reports(self):
        self.report("02", [("UNKNOWN", None, ("A",))])
        self.report("03", [("OFFLINE", "No", ("A",))])
        unknown = self.analyze("02")
        offline = self.analyze("03")
        self.assertNotIn("online", unknown["summary"])
        self.assertIsNone(unknown["groups"][0]["online"])
        self.assertEqual(offline["summary"]["online"]["total_unique_players"], 0)
        self.assertIsNone(offline["summary"]["online"]["average_redundancy_pct"])


if __name__ == "__main__":
    unittest.main()
