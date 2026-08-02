#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import html
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("smoke_test_parenttech.py")
SPEC = importlib.util.spec_from_file_location("smoke_test_parenttech", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


class FakeBrowser:
    def close(self) -> None:
        pass


class FakeChromium:
    def launch(self, headless: bool = True) -> FakeBrowser:
        return FakeBrowser()


class FailingChromium:
    def launch(self, headless: bool = True) -> FakeBrowser:
        raise RuntimeError("browser missing")


class FakePlaywright:
    chromium = FakeChromium()


class FailingPlaywright:
    chromium = FailingChromium()


class FakeSyncPlaywright:
    def __init__(self, playwright=None) -> None:
        self.playwright = playwright or FakePlaywright()

    def __enter__(self) -> FakePlaywright:
        return self.playwright

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class SmokeTestParentTechTests(unittest.TestCase):
    def test_console_filter_only_ignores_expected_youtube_compute_pressure_denial(self) -> None:
        self.assertTrue(smoke.is_ignored_third_party_console_error(
            "Permissions policy violation: compute-pressure is not allowed in this document."
        ))
        self.assertFalse(smoke.is_ignored_third_party_console_error("Uncaught TypeError: render is not a function"))

    def test_screenshot_paths_include_canonical_live_surfaces(self) -> None:
        self.assertEqual(smoke.VIEWPORTS["tablet"], {"width": 820, "height": 1180})
        self.assertIn("/status/", smoke.SCREENSHOT_PATHS)
        self.assertIn("/live/", smoke.SCREENSHOT_PATHS)
        self.assertIn("/checklists/", smoke.SCREENSHOT_PATHS)
        self.assertIn("/guides/password-recovery", smoke.SCREENSHOT_PATHS)
        self.assertIn("/guides/7-day-parent-tech-setup", smoke.SCREENSHOT_PATHS)
        self.assertNotIn("/status", smoke.SCREENSHOT_PATHS)
        self.assertNotIn("/live", smoke.SCREENSHOT_PATHS)

    def test_screenshot_reset_returns_page_to_top(self) -> None:
        class Page:
            def __init__(self) -> None:
                self.scripts = []
                self.styles = []

            def evaluate(self, script: str) -> None:
                self.scripts.append(script)

            def add_style_tag(self, *, content: str) -> None:
                self.styles.append(content)

        page = Page()
        smoke.reset_scroll_before_screenshot(page)
        self.assertEqual(page.scripts, ["() => window.scrollTo(0, 0)"])
        self.assertEqual(page.styles, [".site-header{position:static!important}"])

    def test_required_link_preserves_campaign_query_for_relative_urls(self) -> None:
        expected = (
            "/products/parent-tech-quick-start-kit"
            "?utm_source=parenttech-site&utm_medium=organic-guide"
            "&utm_campaign=ptc-organic-20260726-family-setup"
        )
        correct = (
            "http://127.0.0.1:8000/products/parent-tech-quick-start-kit"
            "?utm_source=parenttech-site&utm_medium=organic-guide"
            "&utm_campaign=ptc-organic-20260726-family-setup"
        )
        wrong_campaign = correct.replace("ptc-organic-20260726-family-setup", "wrong-campaign")
        self.assertTrue(smoke.required_link_present(expected, [correct]))
        self.assertFalse(smoke.required_link_present(expected, [wrong_campaign]))

    def test_complete_weekly_catalog_is_materialized_for_one_time_deploy(self) -> None:
        manifest = json.loads((smoke.SITE_DIR / "assets" / "weekly-editorial.json").read_text(encoding="utf-8"))
        topics = manifest["topics"]
        self.assertEqual(len(topics), 40)
        self.assertEqual({item["week"] for item in topics}, set(range(8, 48)))
        self.assertEqual(len({item["topic_id"] for item in topics}), 40)
        self.assertEqual(len({item["title"] for item in topics}), 40)
        self.assertEqual(len({item["primary_question"] for item in topics}), 40)
        self.assertTrue(all(item.get("reviewed_at") == "2026-08-02" for item in topics))
        self.assertTrue(all(len(item.get("sources", [])) >= 2 for item in topics))
        self.assertTrue(all((smoke.SITE_DIR / "guides" / f"{item['topic_id']}.html").is_file() for item in topics))
        self.assertTrue(all((smoke.SITE_DIR / item["thumbnail_public_path"].lstrip("/")).is_file() for item in topics))
        sitemap = (smoke.SITE_DIR / "sitemap.xml").read_text(encoding="utf-8")
        redirects = (smoke.SITE_DIR / "_redirects").read_text(encoding="utf-8")
        self.assertIn("/checklists /checklists/ 301", redirects)
        self.assertIn("https://parenttechchecklist.com/checklists/", sitemap)
        for item in topics:
            self.assertEqual(sitemap.count(f"https://parenttechchecklist.com{item['companion_path']}"), 1)
        self.assertIn("https://parenttechchecklist.com/guides/medication-reminders", sitemap)
        self.assertTrue((smoke.SITE_DIR / "favicon.ico").is_file())

    def test_weekly_guides_meet_people_first_content_gate(self) -> None:
        manifest = json.loads((smoke.SITE_DIR / "assets" / "weekly-editorial.json").read_text(encoding="utf-8"))
        sentence_sets = []
        sentence_counts: dict[str, int] = {}
        for topic in manifest["topics"]:
            markup = (smoke.SITE_DIR / "guides" / f"{topic['topic_id']}.html").read_text(encoding="utf-8")
            visible = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", markup, flags=re.DOTALL)))
            words = re.findall(r"\b[\w'-]+\b", visible)
            self.assertGreaterEqual(len(words), 650, topic["topic_id"])
            for source in topic["sources"]:
                self.assertIn(f'href="{source["url"]}"', markup, topic["topic_id"])
            sentences = {
                re.sub(r"\s+", " ", sentence).strip().lower()
                for sentence in re.split(r"(?<=[.!?])\s+", visible)
                if len(sentence.split()) >= 10
            }
            sentence_sets.append(sentences)
            for sentence in sentences:
                sentence_counts[sentence] = sentence_counts.get(sentence, 0) + 1
        repeat_ratios = [
            sum(1 for sentence in sentences if sentence_counts[sentence] > 1) / max(1, len(sentences))
            for sentences in sentence_sets
        ]
        self.assertLess(sorted(repeat_ratios)[len(repeat_ratios) // 2], 0.25)

    def test_live_and_status_share_editorial_topic_without_overriding_events(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        home = (smoke.SITE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn("payload.editorial_topic", live)
        self.assertIn("payload.priority_event", live)
        self.assertIn("payload.editorial_topic", status)
        self.assertIn("payload.priority_event", status)
        self.assertIn("/assets/weekly-editorial.json", home)
        self.assertIn("Asia/Taipei", home)

    def test_live_pages_use_snapshot_stamp_for_hydration(self) -> None:
        live_checks = {item["path"] for item in smoke.PAGE_CHECKS if item["path"] in {"/status/", "/live/"}}
        self.assertEqual(live_checks, {"/status/", "/live/"})
        review = next(item for item in smoke.PAGE_CHECKS if item["path"] == "/products/personalized-setup-review")
        self.assertIn("/contact", review["required_links"])

    def test_live_page_is_indexable_and_embeds_privacy_enhanced_player(self) -> None:
        html = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        sitemap = (smoke.SITE_DIR / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="index,follow">', html)
        self.assertIn('<link rel="canonical" href="https://parenttechchecklist.com/live/">', html)
        self.assertIn("data-player-src=\"https://www.youtube-nocookie.com/embed/4HYkV-6NRcY", html)
        self.assertIn('id="stream-play"', html)
        self.assertIn('/assets/live-status-poster.jpg', html)
        self.assertIn("https://parenttechchecklist.com/live/", sitemap)

    def test_live_page_exposes_video_and_live_broadcast_metadata(self) -> None:
        html = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        match = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html, re.DOTALL)
        self.assertIsNotNone(match)
        metadata = json.loads(match.group(1))
        self.assertEqual(metadata["@type"], "VideoObject")
        self.assertEqual(metadata["embedUrl"], "https://www.youtube-nocookie.com/embed/4HYkV-6NRcY")
        self.assertEqual(metadata["publication"]["@type"], "BroadcastEvent")
        self.assertTrue(metadata["publication"]["isLiveBroadcast"])
        self.assertEqual(metadata["publication"]["startDate"], "2026-07-10T11:59:36Z")
        self.assertIn('property="og:type" content="video.other"', html)
        self.assertIn("https://i.ytimg.com/vi/4HYkV-6NRcY/maxresdefault.jpg", html)

    def test_live_page_deduplicates_identical_product_and_model_copy(self) -> None:
        html = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("model.localeCompare(product", html)
        self.assertIn("facts.push(['Model', model])", html)

    def test_live_recall_headline_separates_product_from_family_action(self) -> None:
        html = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("return `Recall check: ${card?.product_name || 'match the product'}`", html)
        self.assertNotIn("before using it", html)
        self.assertIn("Family action: ${actionLabel(event.consumer_action_code)}", html)

    def test_live_page_does_not_present_kv_scene_snapshot_as_live_countdown(self) -> None:
        html = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Latest verified segment", html)
        self.assertIn("Stream rotates every ${duration}s", html)
        self.assertIn("Snapshot age:", html)
        self.assertIn("function nextSegmentLabel(scene, retention)", html)
        self.assertIn("official: 'official source check'", html)
        self.assertNotIn("Next: ${retention.next_teaser", html)
        self.assertNotIn("Current scene", html)
        self.assertNotIn("in ${remaining || 0}s", html)

    def test_status_page_does_not_present_kv_scene_snapshot_as_live_countdown(self) -> None:
        html = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Stream snapshot:", html)
        self.assertIn("${Math.round(age)}s old", html)
        self.assertIn("Rotates every ${duration}s", html)
        self.assertNotIn("Live scene:", html)
        self.assertNotIn("seconds_remaining", html)

    def test_live_surfaces_refresh_only_while_visible(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        self.assertIn("setInterval(refreshIfVisible, 60000)", live)
        self.assertIn("setInterval(hydrateIfVisible, 240000)", status)
        self.assertIn("document.visibilityState === 'visible'", live)
        self.assertIn("document.visibilityState === 'visible'", status)
        self.assertIn("visibilitychange", live)
        self.assertIn("visibilitychange", status)

    def test_live_surfaces_bound_and_deduplicate_snapshot_requests(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        self.assertIn("if (refreshInFlight) return", live)
        self.assertIn("if (statusHydrationInFlight) return", status)
        self.assertIn("controller.abort(), 10000", live)
        self.assertIn("controller.abort(), 10000", status)
        self.assertIn("signal:controller.signal", live)
        self.assertIn("signal: controller.signal", status)
        self.assertIn("refreshInFlight = false", live)
        self.assertIn("statusHydrationInFlight = false", status)

    def test_status_page_fails_closed_when_the_last_successful_snapshot_expires(self) -> None:
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        self.assertIn("let lastSnapshotPayload = null", status)
        self.assertIn("lastSnapshotPayload = payload", status)
        self.assertIn("if (lastSnapshotPayload && !snapshotIsFresh(lastSnapshotPayload))", status)
        self.assertIn("showExpiredSnapshot(lastSnapshotPayload, generated)", status)
        self.assertIn("factList.hidden = true", status)
        self.assertIn("STATUS DATA UNAVAILABLE", status)

    def test_live_page_keeps_only_a_still_fresh_snapshot_after_refresh_failure(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("let lastLiveSnapshotPayload = null", live)
        self.assertIn("lastLiveSnapshotPayload = payload", live)
        self.assertIn("lastLiveSnapshotPayload && snapshotIsFresh(lastLiveSnapshotPayload)", live)
        self.assertIn("Refresh delayed · last verified snapshot remains within the freshness window", live)
        self.assertIn("showFetchUnavailable()", live)
        self.assertIn("toLocaleString('en-US'", live)
        self.assertIn('href="/status?utm_source=live-player', live)
        self.assertIn(".stream{grid-row:1;min-height:0}", live)

    def test_live_mobile_puts_verified_event_directly_after_stream(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertLess(live.index('class="stream"'), live.index('id="event"'))
        self.assertLess(live.index('id="event"'), live.index('class="scene"'))
        self.assertIn(".hero>.event{grid-row:1", live)
        self.assertIn(".stream{grid-row:2}", live)
        self.assertIn(".hero>.weekly-topic{grid-row:3", live)
        self.assertIn(".hero>header.panel{grid-row:4", live)
        self.assertIn(".scene{grid-column:auto;grid-row:5", live)

    def test_live_event_slot_is_reserved_before_status_hydration(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="event pending"', live)
        self.assertIn('aria-busy="true"', live)
        self.assertIn(".event{--event-accent:var(--gold);display:block", live)
        self.assertIn(".hero>header.panel,.stream{min-height:460px}", live)
        self.assertIn(".event{min-height:320px}", live)
        self.assertIn(".stream{grid-row:1;min-height:0}", live)
        self.assertIn("No urgent official update", live)
        self.assertIn("Official update temporarily unavailable", live)

    def test_live_event_uses_calm_state_specific_accents(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-event-kind="pending"', live)
        self.assertIn("eventBox.dataset.eventKind = eventKind(event)", live)
        self.assertIn("eventBox.dataset.eventKind = 'clear'", live)
        self.assertIn("eventBox.dataset.eventKind = 'unavailable'", live)
        self.assertIn('.event[data-event-kind="recall"]', live)
        self.assertIn('.event[data-event-kind="alert"]', live)
        self.assertNotIn("background:rgba(74,52,20,.92)", live)

    def test_live_player_uses_strict_referrer_policy_without_speculative_hints(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("player.referrerPolicy = 'strict-origin-when-cross-origin'", live)
        self.assertIn("player.src = streamPlay.dataset.playerSrc", live)
        self.assertIn("player.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture'", live)
        self.assertNotIn('rel="preconnect" href="https://www.youtube-nocookie.com"', live)
        self.assertNotIn('rel="dns-prefetch" href="//www.youtube-nocookie.com"', live)
        self.assertNotIn('rel="preload" href="https://i.ytimg.com', live)

    def test_live_player_has_visible_focus_and_touch_safe_text_status_link(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        self.assertIn("a:focus-visible{outline:3px solid #f8fafc", live)
        self.assertIn(".stream-frame:focus-within{outline:4px solid var(--gold)", live)
        self.assertIn(".stream-caption a{display:inline-flex;min-height:44px", live)
        self.assertIn(".stream-play{position:absolute", live)

    def test_checkout_handoff_never_redirects_automatically(self) -> None:
        checkout = (smoke.SITE_DIR / "go" / "parent-tech-quick-start-kit.html").read_text(encoding="utf-8")
        self.assertNotIn("autoredirect", checkout)
        self.assertNotIn("setTimeout", checkout)
        self.assertIn("Nothing on this page will redirect you automatically", checkout)

    def test_status_details_are_collapsed_behind_clear_summaries(self) -> None:
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        self.assertIn("View Google, Zoom, and Apple details", status)
        self.assertIn("View FTC, CISA, and CPSC details", status)
        self.assertIn("What happened", status)
        self.assertIn("What to do now", status)

    def test_home_live_band_does_not_claim_unverified_runtime_state(self) -> None:
        home = (smoke.SITE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn("Family tech status desk", home)
        self.assertNotIn("Live status is running", home)
        self.assertIn('href="/go/home-live-youtube">Watch live</a>', home)

    def test_status_mobile_prioritizes_current_update_before_metadata(self) -> None:
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        styles = (smoke.SITE_DIR / "styles.css").read_text(encoding="utf-8")
        self.assertLess(status.index('class="current-update"'), status.index('class="status-meta-grid"'))
        self.assertIn(".current-update {\n    grid-column: 1;\n    grid-row: 2;", styles)
        self.assertIn(".status-meta-grid {\n    grid-column: 1;\n    grid-row: 3;", styles)

    def test_status_current_update_is_stable_and_summary_first(self) -> None:
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        styles = (smoke.SITE_DIR / "styles.css").read_text(encoding="utf-8")
        self.assertIn("const facts = '';", status)
        self.assertNotIn("function eventFactsHtml", status)
        self.assertIn("min-height: 650px", styles)
        self.assertIn("min-height: 110px", styles)
        self.assertIn(".current-update .hero-actions", styles)
        self.assertIn(".event-facts[hidden]", styles)
        self.assertIn(".facts[hidden],.weekly-topic[hidden]{display:none}", live)

    def test_status_mobile_actions_precede_technical_snapshot_details(self) -> None:
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        styles = (smoke.SITE_DIR / "styles.css").read_text(encoding="utf-8")
        self.assertLess(status.index('class="hero-actions"'), status.index('id="snapshot-stamp"'))
        self.assertIn("Official service and safety updates", status)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr)) !important", styles)
        self.assertIn("min-height: 560px", styles)
        self.assertIn("20260717-status-cta2", status)

    def test_live_ctas_use_privacy_safe_redirect_paths(self) -> None:
        live = (smoke.SITE_DIR / "live" / "index.html").read_text(encoding="utf-8")
        status = (smoke.SITE_DIR / "status" / "index.html").read_text(encoding="utf-8")
        redirects = (smoke.SITE_DIR / "_redirects").read_text(encoding="utf-8")
        for path in (
            "/go/home-live-youtube",
            "/go/medication-live-youtube",
            "/go/live-youtube",
            "/go/status-youtube",
            "/go/live-senior-phone",
            "/go/live-video-calling",
            "/go/live-scam-safety",
        ):
            self.assertIn(path, redirects)
        self.assertIn('href="/go/live-youtube"', live)
        self.assertIn('href="/go/status-youtube"', status)
        home = (smoke.SITE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/go/home-live-youtube"', home)
        self.assertIn('href="/live"', home)
        medication = (smoke.SITE_DIR / "guides" / "medication-reminders.html").read_text(encoding="utf-8")
        self.assertIn('href="/go/medication-live-youtube"', medication)
        self.assertNotIn("window.gtag", live)

    def test_public_html_has_no_placeholder_youtube_video_ids(self) -> None:
        offenders = []
        for path in smoke.SITE_DIR.rglob("*.html"):
            if "youtube.com/watch?v=PLACEHOLDER" in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(smoke.SITE_DIR).as_posix())
        self.assertEqual(offenders, [])

    def test_home_hero_uses_responsive_webp_without_changing_social_image(self) -> None:
        html = (smoke.SITE_DIR / "index.html").read_text(encoding="utf-8")
        webp_800 = smoke.SITE_DIR / "assets" / "ptc-hero-family-tech-800.webp"
        webp_1280 = smoke.SITE_DIR / "assets" / "ptc-hero-family-tech-1280.webp"
        self.assertIn('type="image/webp"', html)
        self.assertIn("ptc-hero-family-tech-800.webp 800w", html)
        self.assertIn("ptc-hero-family-tech-1280.webp 1280w", html)
        self.assertIn('og:image" content="https://parenttechchecklist.com/assets/ptc-hero-family-tech.jpg"', html)
        self.assertTrue(webp_800.exists())
        self.assertTrue(webp_1280.exists())
        self.assertLess(webp_800.stat().st_size, 40_000)
        self.assertLess(webp_1280.stat().st_size, 70_000)

    def test_run_smoke_writes_report_when_page_check_raises(self) -> None:
        original_assets = smoke.assert_http_assets
        original_sync = smoke.sync_playwright
        original_check_page = smoke.check_page
        original_page_checks = smoke.PAGE_CHECKS
        original_viewports = smoke.VIEWPORTS
        smoke.assert_http_assets = lambda base_url: []
        smoke.sync_playwright = lambda: FakeSyncPlaywright()
        smoke.check_page = lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("page timeout"))
        smoke.PAGE_CHECKS = [{"path": "/disclosure"}]
        smoke.VIEWPORTS = {"desktop": {"width": 1440, "height": 1100}}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = smoke.run_smoke("https://example.test", Path(tmp), False, 100)
                self.assertFalse(report["ok"])
                self.assertEqual(len(report["failed"]), 1)
                self.assertIn("desktop /disclosure page check", report["failed"][0]["name"])
                self.assertTrue((Path(tmp) / "smoke-report.json").exists())
                self.assertTrue((Path(tmp) / "smoke-report.md").exists())
        finally:
            smoke.assert_http_assets = original_assets
            smoke.sync_playwright = original_sync
            smoke.check_page = original_check_page
            smoke.PAGE_CHECKS = original_page_checks
            smoke.VIEWPORTS = original_viewports

    def test_run_smoke_writes_report_when_browser_launch_fails(self) -> None:
        original_assets = smoke.assert_http_assets
        original_sync = smoke.sync_playwright
        smoke.assert_http_assets = lambda base_url: []
        smoke.sync_playwright = lambda: FakeSyncPlaywright(FailingPlaywright())
        try:
            with tempfile.TemporaryDirectory() as tmp:
                report = smoke.run_smoke("https://example.test", Path(tmp), False, 100)
                self.assertFalse(report["ok"])
                self.assertEqual(len(report["failed"]), 1)
                self.assertEqual(report["failed"][0]["name"], "browser smoke runner")
                self.assertEqual(report["failed"][0]["details"]["error_type"], "RuntimeError")
                self.assertTrue((Path(tmp) / "smoke-report.json").exists())
                self.assertTrue((Path(tmp) / "smoke-report.md").exists())
        finally:
            smoke.assert_http_assets = original_assets
            smoke.sync_playwright = original_sync


if __name__ == "__main__":
    unittest.main()
