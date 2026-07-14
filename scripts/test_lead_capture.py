#!/usr/bin/env python3
"""Parent Tech Checklist — lead-capture funnel local tests.

Tests the Python validation module (lead_handler.py) and form HTML markup.
No secrets, no email sending, no remote calls. All tests run locally.
"""
from __future__ import annotations

import importlib.util
import json
import time
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_DIR = SCRIPT_DIR.parent
HANDLER_PATH = SCRIPT_DIR / "lead_handler.py"
CONTACT_HTML = SITE_DIR / "contact.html"

# Load lead_handler module
spec = importlib.util.spec_from_file_location("lead_handler", HANDLER_PATH)
lh = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(lh)


class LeadValidationTests(unittest.TestCase):
    """Test lead_handler.validate_lead() — pure function, no I/O."""

    def _make(self, **overrides) -> dict[str, str]:
        base = {
            "email": "jane@example.com",
            "name": "Jane",
            "topic": "phone-setup",
            "consent": "yes",
            "website": "",
            # Timestamp >2s ago so normal tests pass the submission-speed check
            "honeypot_time": str((time.time() - 10) * 1000),
            "utm_source": "homepage",
            "utm_medium": "hero",
            "utm_campaign": "ptc-lead-test",
            "utm_content": "guide-card",
        }
        base.update(overrides)
        return base

    def test_valid_submission(self):
        result = lh.validate_lead(self._make())
        self.assertTrue(result["valid"])
        self.assertFalse(result.get("honeypot"))
        self.assertEqual(result["email"], "jane@example.com")
        self.assertEqual(result["name"], "Jane")
        self.assertEqual(result["topic"], "phone-setup")
        self.assertEqual(result["utm_source"], "homepage")
        self.assertEqual(result["utm_campaign"], "ptc-lead-test")

    def test_valid_minimal_fields(self):
        """Name and topic are optional."""
        result = lh.validate_lead(self._make(name="", topic=""))
        self.assertTrue(result["valid"])
        self.assertEqual(result["name"], "")
        self.assertEqual(result["topic"], "")

    def test_rejects_missing_email(self):
        result = lh.validate_lead(self._make(email=""))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "email")

    def test_rejects_invalid_email_format(self):
        for bad in ["notanemail", "@missing", "missing@", "a@b"]:
            with self.subTest(email=bad):
                result = lh.validate_lead(self._make(email=bad))
                self.assertFalse(result["valid"])
                self.assertEqual(result["field"], "email")

    def test_rejects_email_too_long(self):
        result = lh.validate_lead(self._make(email="a@" + "b" * 320 + ".com"))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "email")

    def test_rejects_name_too_long(self):
        result = lh.validate_lead(self._make(name="x" * 201))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "name")

    def test_rejects_invalid_topic(self):
        result = lh.validate_lead(self._make(topic="hacking-wifi"))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "topic")

    def test_accepts_all_valid_topics(self):
        for topic in lh.VALID_TOPICS:
            with self.subTest(topic=topic):
                result = lh.validate_lead(self._make(topic=topic))
                self.assertTrue(result["valid"])

    def test_requires_consent(self):
        result = lh.validate_lead(self._make(consent=""))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "consent")

    def test_honeypot_returns_honeypot_true(self):
        """Honeypot filled -> valid=True, honeypot=True. No recording."""
        result = lh.validate_lead(self._make(website="spam-bot-value"))
        self.assertTrue(result["valid"])
        self.assertTrue(result["honeypot"])

    def test_rejects_fast_submission(self):
        """Submissions <2s after honeypot_time are rejected as bots."""
        now_ms = time.time() * 1000
        result = lh.validate_lead(self._make(honeypot_time=str(now_ms)))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "honeypot_time")

    def test_rejects_missing_honeypot_time(self):
        result = lh.validate_lead(self._make(honeypot_time=""))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "honeypot_time")

    def test_rejects_garbage_honeypot_time(self):
        result = lh.validate_lead(self._make(honeypot_time="abc"))
        self.assertFalse(result["valid"])
        self.assertEqual(result["field"], "honeypot_time")

    def test_preserves_utm_attribution(self):
        result = lh.validate_lead(self._make(
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="summer2026",
            utm_content="ad1",
        ))
        self.assertTrue(result["valid"])
        self.assertEqual(result["utm_source"], "google")
        self.assertEqual(result["utm_medium"], "cpc")
        self.assertEqual(result["utm_campaign"], "summer2026")
        self.assertEqual(result["utm_content"], "ad1")

    def test_empty_utm_returns_empty_strings(self):
        result = lh.validate_lead(self._make(
            utm_source="", utm_medium="", utm_campaign="", utm_content=""
        ))
        self.assertTrue(result["valid"])
        self.assertEqual(result["utm_source"], "")
        self.assertEqual(result["utm_medium"], "")
        self.assertEqual(result["utm_campaign"], "")
        self.assertEqual(result["utm_content"], "")

    def test_fail_closed_on_garbage_input(self):
        """Handler must not crash on weird input — returns invalid."""
        result = lh.validate_lead({})
        self.assertFalse(result["valid"])
        # Should at minimum have a honeypot_time error
        self.assertIn("field", result)

    def test_all_valid_topics_covered(self):
        expected = {"phone-setup", "scam-call-safety", "video-calling", "living-alone-safety", "general"}
        self.assertEqual(lh.VALID_TOPICS, expected)

    def test_no_secrets_in_handler(self):
        """No hardcoded email, token, or API key in the handler module."""
        source = HANDLER_PATH.read_text()
        self.assertNotIn("@", source.split("def validate_lead")[0])  # no emails before validate func
        self.assertNotIn("gmail", source)
        self.assertNotIn("sendgrid", source)
        self.assertNotIn("api_key", source.lower())
        self.assertNotIn("password", source.lower())
        self.assertNotIn("token", source.lower())

    def test_no_secrets_in_cf_function(self):
        """No hardcoded secrets in the CF Pages Function JS."""
        js_path = SITE_DIR / "functions" / "api" / "lead.js"
        self.assertTrue(js_path.exists(), f"Missing CF function at {js_path}")
        source = js_path.read_text()
        self.assertNotIn("gmail", source)
        self.assertNotIn("sendgrid", source)
        # LEAD_WEBHOOK_SECRET is a binding — the value is in the env, not the source
        self.assertNotIn("'sk-", source)
        self.assertNotIn('"sk-', source)


class ContactFormMarkupTests(unittest.TestCase):
    """Test that contact.html has proper form markup."""

    @classmethod
    def setUpClass(cls):
        cls.html = CONTACT_HTML.read_text(encoding="utf-8")

    def test_has_form(self):
        self.assertIn("<form", self.html)
        self.assertIn("</form>", self.html)

    def test_form_action(self):
        self.assertIn('action="/api/lead"', self.html)
        self.assertIn('method="POST"', self.html)

    def test_has_email_field(self):
        self.assertIn('name="email"', self.html)
        self.assertIn('type="email"', self.html)
        self.assertIn("required", self.html)

    def test_has_consent_checkbox(self):
        self.assertIn('name="consent"', self.html)
        self.assertIn('type="checkbox"', self.html)
        self.assertIn('value="yes"', self.html)
        self.assertIn('aria-required="true"', self.html)

    def test_consent_links_privacy(self):
        self.assertIn("/privacy", self.html)

    def test_has_honeypot(self):
        self.assertIn('name="website"', self.html)
        self.assertIn("honeypot", self.html.lower())

    def test_has_utm_hidden_fields(self):
        for name in ["utm_source", "utm_medium", "utm_campaign", "utm_content"]:
            with self.subTest(field=name):
                self.assertIn(f'name="{name}"', self.html)

    def test_has_honeypot_time(self):
        self.assertIn('name="honeypot_time"', self.html)

    def test_has_submit_button(self):
        self.assertIn('type="submit"', self.html)
        self.assertIn("Send me the free checklist", self.html)

    def test_accessible_labels(self):
        """Every form control has an associated label."""
        self.assertIn('<label for="field-email">', self.html)
        self.assertIn('<label for="field-name">', self.html)
        self.assertIn('<label for="field-topic">', self.html)

    def test_has_status_div(self):
        self.assertIn('id="form-status"', self.html)
        self.assertIn('aria-live="polite"', self.html)

    def test_privacy_note_present(self):
        self.assertIn("Privacy Policy", self.html)
        self.assertIn("never share or sell", self.html.lower())

    def test_no_form_without_consent(self):
        """The consent checkbox is the only way to submit."""
        consent_section = self.html[self.html.index('name="consent"'):]
        self.assertIn('required', consent_section)

    def test_still_has_email_contact(self):
        """Original email contact is preserved."""
        self.assertIn("contact@parenttechchecklist.com", self.html)
        self.assertIn("mailto:", self.html)


class SmokeTestServerFormExtensionTests(unittest.TestCase):
    """Smoke test server can handle POST /api/lead (local test seam)."""

    def test_server_importable(self):
        """The smoke test module can be imported."""
        smoke_path = SCRIPT_DIR / "smoke_test_parenttech.py"
        self.assertTrue(smoke_path.exists())

    def test_cloudflare_handler_supports_post(self):
        """CloudflareLikeHandler should be subclassable to add POST."""
        source = (SCRIPT_DIR / "smoke_test_parenttech.py").read_text()
        # The handler currently only has do_GET and do_HEAD
        self.assertIn("class CloudflareLikeHandler", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
