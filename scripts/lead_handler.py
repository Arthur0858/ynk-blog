#!/usr/bin/env python3
"""Parent Tech Checklist lead-capture validation — shared logic for local testing.

Pure functions (no side effects, no I/O). Mirrors the Cloudflare Pages Function
at functions/api/lead.js. Local tests exercise this module; the JS Function
implements the same validation at deploy time.

Fail-closed: never counts undelivered as a verified lead.
"""
from __future__ import annotations

import re
import time
from typing import Any

VALID_TOPICS = {
    "phone-setup",
    "scam-call-safety",
    "video-calling",
    "living-alone-safety",
    "general",
}


def validate_lead(data: dict[str, str]) -> dict[str, Any]:
    """Validate a lead form submission. Returns {valid, error?, field?, honeypot?, ...}.

    Accepts a dict of string values (as parsed from FormData). Pure — no I/O.
    """
    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip()
    topic = (data.get("topic") or "").strip()
    consent = (data.get("consent") or "").strip()
    honeypot_website = (data.get("website") or "").strip()
    honeypot_time_raw = (data.get("honeypot_time") or "").strip()

    # Honeypot: visible field bots may fill
    if honeypot_website:
        return {"valid": True, "honeypot": True}

    # Time-based rate limiting: field filled by JS on render
    if not honeypot_time_raw:
        return {"valid": False, "error": "Submission validation failed", "field": "honeypot_time"}
    try:
        submitted_ms = float(honeypot_time_raw)
    except (ValueError, TypeError):
        return {"valid": False, "error": "Submission validation failed", "field": "honeypot_time"}
    age_ms = (time.time() * 1000) - submitted_ms
    # ponytail: <2s = likely bot, upgrade to challenge-based check if false-positives appear
    if age_ms < 2000:
        return {"valid": False, "error": "Submission validation failed", "field": "honeypot_time"}

    # Email: required
    if not email:
        return {"valid": False, "error": "Email is required", "field": "email"}
    if len(email) > 320:
        return {"valid": False, "error": "Email too long", "field": "email"}
    # ponytail: basic pattern, not RFC 5322
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return {"valid": False, "error": "Invalid email format", "field": "email"}

    # Name: optional
    if name and len(name) > 200:
        return {"valid": False, "error": "Name too long", "field": "name"}

    # Topic: must be known
    if topic and topic not in VALID_TOPICS:
        return {"valid": False, "error": "Invalid topic", "field": "topic"}

    # Consent: required
    if consent != "yes":
        return {"valid": False, "error": "Privacy consent is required", "field": "consent"}

    return {
        "valid": True,
        "honeypot": False,
        "name": name,
        "email": email,
        "topic": topic,
        "utm_source": (data.get("utm_source") or "").strip(),
        "utm_medium": (data.get("utm_medium") or "").strip(),
        "utm_campaign": (data.get("utm_campaign") or "").strip(),
        "utm_content": (data.get("utm_content") or "").strip(),
    }
