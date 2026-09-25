"""Synthetic regression tests. No network, browser, or real applicant data."""
import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate", REPO / "scripts/validate.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        v.errors.clear()
        v.warnings.clear()
        self.bio = json.loads((REPO / "config/bio.template.json").read_text(encoding="utf-8"))
        self.queue = json.loads((REPO / "data/jobs.example.json").read_text(encoding="utf-8"))

    def validate_queue(self, queue):
        with contextlib.redirect_stdout(io.StringIO()):
            v.check_jobs(queue)

    def test_shipped_examples_validate_semantically(self):
        with contextlib.redirect_stdout(io.StringIO()):
            v.check_shipped_json()
        self.assertEqual([], v.errors)

    def test_tier2_lifecycle(self):
        for state in ("pending", "quarantined", "applied", "skipped", "needs_review", "failed"):
            with self.subTest(state=state):
                v.errors.clear()
                job = copy.deepcopy(self.queue["jobs"][2])
                job.update(status=state, quarantine_reason="session not authenticated")
                self.validate_queue({"schema_version": "2.0.0", "jobs": [job]})
                self.assertEqual([], v.errors)

    def test_tier_and_account_must_agree(self):
        for tier, account in ((1, True), (2, False), (True, False), ([], False)):
            with self.subTest(tier=tier, account=account):
                v.errors.clear()
                queue = copy.deepcopy(self.queue)
                queue["jobs"][0].update(ats_tier=tier, requires_account=account)
                self.validate_queue(queue)
                self.assertTrue(v.errors)

    def test_chat_only_cannot_be_pending_or_applied(self):
        for state in ("pending", "applied"):
            v.errors.clear()
            self.queue["jobs"][3]["status"] = state
            self.validate_queue(self.queue)
            self.assertTrue(any("conversational" in e for e in v.errors))

    def test_manual_form_after_chat_is_eligible(self):
        job = self.queue["jobs"][0]
        job.update(encountered_conversational=True, apply_shape="form")
        self.validate_queue(self.queue)
        self.assertEqual([], v.errors)

    def test_conversational_midflow_quarantine_is_valid(self):
        self.queue["jobs"][3].update(status="quarantined", quarantine_reason="chat appeared")
        self.validate_queue(self.queue)
        self.assertEqual([], v.errors)

    def test_old_queue_requires_upgrade_without_mutation(self):
        self.queue["schema_version"] = "1.0.0"
        del self.queue["jobs"][0]["apply_shape"]
        original = copy.deepcopy(self.queue)
        self.validate_queue(self.queue)
        self.assertTrue(any("UPGRADING.md" in e for e in v.errors))
        self.assertEqual(original, self.queue)

    def test_old_bio_requires_upgrade_without_mutation(self):
        self.bio["schema_version"] = "1.0.0"
        policy = self.bio["agent_policy"]
        policy["allowed_ats"] = policy.pop("ats_support")["tier_1_no_login"]
        original = copy.deepcopy(self.bio)
        v.check_bio(self.bio, template=True)
        self.assertTrue(any("UPGRADING.md" in e for e in v.errors))
        self.assertEqual(original, self.bio)

    def test_unknown_legacy_history_preserved_but_not_pending(self):
        job = self.queue["jobs"][0]
        job.update(status="applied", apply_shape="unknown", ats_tier=None)
        self.validate_queue(self.queue)
        self.assertEqual([], v.errors)
        job["status"] = "pending"
        self.validate_queue(self.queue)
        self.assertTrue(v.errors)

    def test_malformed_queues_report_errors(self):
        for queue in ([], {"jobs": [None]}, {"jobs": [{"status": []}]},
                      {"jobs": [{"status": None}, {"status": "pending"}]}, {"jobs": {}}):
            with self.subTest(queue=queue):
                v.errors.clear()
                self.validate_queue(queue)
                self.assertTrue(v.errors)

    def test_malformed_bio_reports_errors(self):
        for bio in ([], {"identity": []}, {"agent_policy": "bad"}):
            v.errors.clear()
            v.check_bio(bio, template=True)
            self.assertTrue(v.errors)

    def test_every_mode_requires_readback(self):
        for mode in v.VALID_AUTONOMY:
            v.errors.clear()
            self.bio["agent_policy"]["autonomy_level"] = mode
            self.bio["agent_policy"]["post_run_audit"]["record_full_readback_for_every_submission"] = False
            v.check_bio(self.bio, template=True)
            self.assertTrue(any("Every autonomy level" in e for e in v.errors))

    def test_each_boundary_is_enforced(self):
        for key in v.REQUIRED_BOUNDARIES:
            v.errors.clear()
            bio = copy.deepcopy(self.bio)
            bio["agent_policy"]["hard_boundaries"][key] = True
            v.check_bio(bio, template=True)
            self.assertTrue(any(key in e for e in v.errors))

    def test_adapter_name_does_not_install_adapter(self):
        self.bio["agent_policy"]["ats_support"]["tier_2_session_based"] = ["workday"]
        v.check_bio(self.bio, template=True)
        self.assertTrue(any("No tier-2 adapters" in e for e in v.errors))

    def test_boolean_strings_are_not_dry_run(self):
        self.bio["agent_policy"]["dry_run"] = "false"
        v.check_bio(self.bio, template=True)
        self.assertTrue(any("dry_run" in e for e in v.errors))


class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(v, "ROOT", self.root)
        self.root_patch.start()
        self.git("init", "-q")
        (self.root / "config").mkdir()
        self.bio = {"identity": {"email": "synthetic-" + "review@invalid.example"}}
        self.write_bio()
        v.errors.clear()
        v.warnings.clear()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def write_bio(self):
        (self.root / "config/bio.json").write_text(json.dumps(self.bio), encoding="utf-8")

    def tracked(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.git("add", "--", name)
        return path

    def test_spaces_unicode_and_templates_are_scanned(self):
        for name in ("docs/project notes.md", "docs/résumé.md", "config/bio.template.json"):
            self.tracked(name, self.bio["identity"]["email"])
        v.check_no_pii_in_tracked_files()
        self.assertEqual(3, len(v.errors))
        self.assertFalse(any(self.bio["identity"]["email"] in e for e in v.errors))

    def test_staged_content_is_scanned_after_worktree_cleanup(self):
        path = self.tracked("notes.md", self.bio["identity"]["email"])
        path.write_text("clean working copy", encoding="utf-8")
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_worktree_content_is_scanned(self):
        path = self.tracked("notes.md", "clean index")
        path.write_text(self.bio["identity"]["email"], encoding="utf-8")
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_git_enumeration_failure_is_error(self):
        failed = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"failed")
        with patch.object(v.subprocess, "run", return_value=failed):
            v.check_no_pii_in_tracked_files()
        self.assertTrue(any("scan incomplete" in e for e in v.errors))

    def test_dummy_setup_does_not_trigger_privacy_errors(self):
        self.bio = json.loads((REPO / "config/bio.template.json").read_text(encoding="utf-8"))
        self.write_bio()
        self.tracked("config/bio.template.json", json.dumps(self.bio))
        self.tracked("README.md", "Jordan Rivera and Example State University")
        (self.root / "data").mkdir()
        (self.root / "data/resume.pdf").write_bytes(b"synthetic existence fixture")
        v.check_bio(self.bio)
        v.check_no_pii_in_tracked_files()
        self.assertEqual([], v.errors)

    def test_synthetic_identity_does_not_exempt_real_other_fields(self):
        self.bio = json.loads((REPO / "config/bio.template.json").read_text(encoding="utf-8"))
        self.bio["education"][0]["institution"] = "Synthetic " + "Regression College"
        self.write_bio()
        self.tracked("config/bio.template.json", self.bio["education"][0]["institution"])
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_real_profile_with_dummy_first_name_is_scanned(self):
        self.bio["identity"]["first_name"] = "Jordan"
        self.write_bio()
        self.tracked("notes.md", "Jordan")
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_short_names_are_not_silently_dropped(self):
        self.bio["identity"]["first_name"] = "Ivo"
        self.write_bio()
        self.tracked("notes.md", "Applicant: Ivo")
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_deleted_worktree_file_still_checks_index(self):
        self.tracked("notes.md", self.bio["identity"]["email"]).unlink()
        v.check_no_pii_in_tracked_files()
        self.assertEqual(1, len(v.errors))

    def test_unreadable_bio_cannot_silently_skip_privacy(self):
        (self.root / "config/bio.json").write_text("null", encoding="utf-8")
        v.check_no_pii_in_tracked_files()
        self.assertTrue(any("scan incomplete" in e for e in v.errors))

    def test_repository_only_still_checks_pii(self):
        self.tracked("notes.md", self.bio["identity"]["email"])
        with patch.object(v, "check_shipped_json"), patch.object(v, "check_gitignore"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, v.main(["--repository-only"]))
        self.assertTrue(any("tracked" in e for e in v.errors))


if __name__ == "__main__":
    unittest.main()
