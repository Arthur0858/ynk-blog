#!/usr/bin/env python3
"""Build the complete ParentTech weekly guide library from one manifest."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_DIR / "assets" / "weekly-editorial.json"
REVIEWED_AT = "2026-08-02"
EDITOR = "Parent Tech Checklist editorial desk"

SOURCES = {
    "cisa_world": ("CISA Secure Our World", "https://www.cisa.gov/secure-our-world"),
    "cisa_phishing": ("CISA: Recognize and Report Phishing", "https://www.cisa.gov/secure-our-world/recognize-and-report-phishing"),
    "cisa_passwords": ("CISA: Use Strong Passwords", "https://www.cisa.gov/secure-our-world/use-strong-passwords"),
    "cisa_mfa": ("CISA: Turn On MFA", "https://www.cisa.gov/secure-our-world/turn-mfa"),
    "ftc_scams": ("FTC Consumer Scams", "https://consumer.ftc.gov/scams"),
    "ftc_phishing": ("FTC: Recognize and Avoid Phishing", "https://consumer.ftc.gov/articles/how-recognize-and-avoid-phishing-scams"),
    "ftc_support": ("FTC: Tech Support Scams", "https://consumer.ftc.gov/articles/how-spot-avoid-and-report-tech-support-scams"),
    "ftc_gift": ("FTC: Gift Card Scams", "https://consumer.ftc.gov/articles/avoiding-and-reporting-gift-card-scams"),
    "ftc_wifi": ("FTC: Secure Your Home Wi-Fi", "https://consumer.ftc.gov/articles/how-secure-your-home-wi-fi-network"),
    "ftc_government": ("FTC: Government Impersonation Scams", "https://consumer.ftc.gov/articles/government-impersonation-scams"),
    "uspis_smishing": ("U.S. Postal Inspection Service: Smishing", "https://www.uspis.gov/news/scam-article/smishing-package-tracking-text-scams"),
    "ready_plan": ("Ready.gov Family Communication Plan", "https://www.ready.gov/plan"),
    "apple_iphone": ("Apple iPhone User Guide", "https://support.apple.com/guide/iphone/welcome/ios"),
    "apple_recovery": ("Apple Account Recovery", "https://support.apple.com/en-us/118574"),
    "apple_subscriptions": ("Apple: Cancel a Subscription", "https://support.apple.com/en-us/118428"),
    "google_android": ("Google Android Help", "https://support.google.com/android/"),
    "google_photos": ("Google Photos Help", "https://support.google.com/photos/"),
    "google_recovery": ("Google Account Recovery", "https://support.google.com/accounts/answer/7682439"),
    "google_subscriptions": ("Google Play Subscriptions", "https://support.google.com/googleplay/answer/7018481"),
    "cpsc_recalls": ("U.S. CPSC Recalls", "https://www.cpsc.gov/Recalls"),
    "cpsc_batteries": ("CPSC: High-Energy Battery Fire Safety", "https://www.cpsc.gov/Regulations-Laws--Standards/Voluntary-Standards/Batteries-Fire-High-Energy-Density"),
    "epa_recycle": ("EPA Electronics Donation and Recycling", "https://www.epa.gov/recycle/electronics-donation-and-recycling"),
    "nist_iot": ("NIST Consumer IoT Cybersecurity", "https://www.nist.gov/itl/applied-cybersecurity/nist-cybersecurity-iot-program/consumer-iot-cybersecurity"),
}

# Each record supplies topic-specific substance. The common page structure remains
# predictable for older readers, while scenarios, evidence and stop rules stay unique.
DETAILS = {
    "password-recovery": ("a recovery email or phone may be outdated before a lockout", "Open the account's security page from a saved bookmark or typed address and keep the currently signed-in device available.", "which recovery route was confirmed and the date it was tested", "the owner can reach the recovery prompt without revealing a password", "Stop if the page asks for a code that arrived unexpectedly or proposes replacing a working recovery route.", ("google_recovery", "apple_recovery")),
    "trusted-remote-support": ("a relative needs to help from another home without normalizing unexpected remote access", "Agree on the helper, the exact task and a start time before opening any screen-sharing tool.", "who initiated the session, what changed and when access ended", "the parent can see the helper leave and can close the support tool", "End the session immediately if an unknown caller initiated it, requests payment or asks to hide the screen.", ("ftc_support", "cisa_phishing")),
    "contacts-favorites": ("important family contacts are buried in a long address book", "Ask the parent which people they actually call for everyday help and emergencies; do not choose on their behalf.", "the three-to-five visible names and the screen where each can be reached", "the parent can place and end one test call independently", "Stop if editing a contact would overwrite another person's number or merge two different people.", ("apple_iphone", "google_android")),
    "photo-sharing-backup": ("photos appear in several apps and nobody knows which copy is protected", "Choose one representative photo and identify the account currently used for backup before moving or deleting anything.", "the backup account, last completed backup and one shared album owner", "a second family device can view the test photo without creating another copy", "Do not remove local photos until the same files are visible in the official backup service and recently deleted folders are understood.", ("google_photos", "apple_iphone")),
    "voicemail-setup": ("important callers leave messages that are too quiet or difficult to identify", "Place the phone in its usual location and use a trusted family phone to create one test voicemail.", "the playback volume, greeting status and trusted callback method", "the parent can hear, pause and return the test call", "Stop before returning a call if the message asks for money, codes or urgent account action.", ("apple_iphone", "ftc_scams")),
    "family-group-chat": ("family updates are mixed with noisy notifications and sensitive information", "Choose one small group for routine coordination and agree which topics belong somewhere else.", "the group owner, membership list and notification rule", "the parent can find the group and recognize who is participating", "Remove unexpected members and move passwords, medical details and emergency instructions out of the chat.", ("apple_iphone", "google_android")),
    "fake-delivery-texts": ("a text claims a package needs an urgent payment or address confirmation", "Leave the message unopened and find the order through the retailer or carrier app that the family already uses.", "the real order status and the official app or typed website used to check it", "the family can verify delivery without using the message link", "Stop whenever a delivery text requests a fee, card number, password or one-time code.", ("uspis_smishing", "ftc_phishing")),
    "fake-bank-government": ("a caller claims to be a bank or agency and demands immediate action", "End the call and locate the number printed on a statement, card or official government website.", "the organization contacted independently and the result of that call", "the account owner receives confirmation through a known official channel", "Do not move money, buy gift cards or share codes to satisfy an incoming caller.", ("ftc_government", "ftc_scams")),
    "remote-support-scams": ("an unsolicited caller says the computer or phone is infected", "Do not install software; close the message and call a family helper using a saved contact.", "the caller's claim, the screen that appeared and whether anything was installed", "the device remains usable without granting new remote access", "Disconnect from the network and seek official support if software was installed or credentials were entered.", ("ftc_support", "cisa_phishing")),
    "marketplace-gift-cards": ("a seller pushes payment outside the marketplace or requests a gift card", "Keep the listing, messages and payment screen inside the official marketplace app.", "the listing URL, seller profile and approved payment method without storing card data", "the transaction can proceed without secrecy, urgency or an unusual payment route", "Leave the transaction if the seller requests gift cards, cryptocurrency, wire transfer or off-platform contact.", ("ftc_gift", "ftc_scams")),
    "current-ftc-alert": ("the family wants to practice responding to a suspicious message without treating it as a confirmed alert", "Use a harmless saved example or screenshot and keep real account details out of the exercise.", "the warning sign noticed and the official route chosen for verification", "the parent can pause, close the message and open the company or agency site independently", "Stop the drill if it creates fear or if a real transaction or account change appears.", ("ftc_phishing", "cisa_phishing")),
    "router-labeling": ("the router and modem are confused during an outage", "Identify each box by following the power and internet cables without unplugging working equipment.", "device purpose, ISP support route and installation date, but never the Wi-Fi password", "a family helper can name the modem and router without resetting either", "Do not press reset or expose network credentials on a visible label.", ("ftc_wifi", "nist_iot")),
    "wifi-dead-zones": ("calls and video fail only in rooms the parent uses", "Choose the same phone, same app and three normal locations for a repeatable signal test.", "the room, time and whether ordinary calling or video worked", "the family can identify a location pattern before buying equipment", "Stop changing settings if the whole service is down or the official ISP status reports an incident.", ("ftc_wifi", "nist_iot")),
    "guest-wifi": ("helpers and connected devices need internet without receiving the main network password", "Open the router's official app or locally bookmarked admin page with the account owner present.", "the guest network name, who may use it and how access will be removed", "a test device joins the guest network without seeing family devices", "Stop if the router requires exposing the main password or changing unrelated firewall settings.", ("ftc_wifi", "nist_iot")),
    "official-isp-outage": ("the family is tempted to reset equipment before checking whether the provider is down", "Save the ISP's official status or support page while service is working.", "the service area, incident time and official case or notice reference", "the family can distinguish a provider incident from one-device trouble", "Wait when an official outage is active; repeated resets can erase useful settings without restoring service.", ("cisa_world", "ready_plan")),
    "outage-offline-plan": ("internet or power loss removes the family's usual messaging route", "Choose one phone number, meeting expectation and printed contact card before an outage occurs.", "the backup contact method, check-in time and person responsible for follow-up", "each person can find the plan without internet access", "Do not put passwords, door codes, medical records or financial account numbers on the contact card.", ("ready_plan", "cisa_world")),
    "new-phone-handoff": ("a new phone is ready but essential calls, photos or recovery paths may still depend on the old one", "Charge both phones, confirm a recent backup and keep the old device signed in until testing is complete.", "which data transferred and which call, message and recovery tests passed", "the parent can complete the three most important tasks on the new phone", "Do not erase, trade in or remove the old phone from accounts until every critical test passes.", ("apple_iphone", "google_android")),
    "accessibility-settings": ("small text, quiet audio or touch timing makes normal tasks harder", "Ask the parent to choose one difficult task and adjust only one setting before testing again.", "the original setting, new setting and task that became easier or harder", "the parent completes the chosen task with less effort and no new confusion", "Undo the change if labels disappear, controls move unexpectedly or another essential task becomes harder.", ("apple_iphone", "google_android")),
    "tablet-setup": ("a tablet home screen contains too many apps and duplicate shortcuts", "List the three activities the parent wants on the tablet and identify the correct app for each.", "the home-screen order and the account owner for each essential app", "calls, photos and messages are reachable from one screen", "Do not remove an app until its data, account and replacement shortcut are understood.", ("apple_iphone", "google_android")),
    "storage-cleanup": ("storage warnings appear but family photos and messages must not be lost", "Confirm backup status and open the official storage summary before selecting files.", "the largest storage categories, last backup and items approved for removal", "free space increases while a sample photo and message remain available", "Stop if backup is incomplete, account ownership is unclear or the device proposes erasing synced originals.", ("google_photos", "apple_iphone")),
    "major-os-update": ("a major phone update may interrupt familiar apps or account access", "Charge above 50 percent, connect to trusted Wi-Fi and confirm a recent backup plus recovery route.", "the backup time, installed version and important apps tested afterward", "calls, messages, photos and one account login work after the update", "Delay the update if backup, charging or recovery information cannot be verified.", ("apple_iphone", "google_android")),
    "smart-lights-plugs": ("the family wants automation without losing a familiar manual control", "Choose one lamp or appliance that is safe to test and confirm its physical switch remains usable.", "the device name, manual fallback and person who owns the companion account", "the device works both from the chosen control and after Wi-Fi returns", "Stop if the device controls heat, cooking, medical equipment or another safety-critical load.", ("nist_iot", "cisa_world")),
    "video-doorbells": ("doorbell alerts are noisy or recordings are shared more widely than expected", "Decide who needs alerts, how long recordings should remain and which entrance is in scope.", "alert recipients, retention setting and one manual way to answer the door", "the right family member receives one test alert without alerting everyone", "Disable unexpected sharing and stop if account ownership or recording access is unclear.", ("nist_iot", "cisa_world")),
    "voice-assistants": ("a voice assistant is useful for a few tasks but may allow purchases or retain activity", "Write down three useful commands and open the official privacy and purchase settings together.", "enabled commands, purchase status and the date voice activity was reviewed", "the parent can use the three commands and knows how to stop listening", "Turn off purchasing and unnecessary integrations when consent or account ownership is unclear.", ("nist_iot", "cisa_world")),
    "thermostat-basics": ("a smart thermostat schedule or app makes basic temperature changes confusing", "Write down the comfortable daytime and nighttime settings and find the physical controls first.", "the schedule, manual override and person who receives device alerts", "the parent can change and restore the temperature without the app", "Stop if the system controls critical heating or cooling and the manual fallback does not work.", ("nist_iot", "cisa_world")),
    "smart-home-official-alert": ("a message claims a connected device has a privacy or security problem", "Find the exact maker, model and installed software version from the device or official app.", "the model, version and official notice that was checked", "the family can match every identifying detail before taking action", "Do not disable or replace a device based only on a message, social post or mismatched model.", ("nist_iot", "cisa_phishing")),
    "official-updates": ("a message offers an update link outside the device's normal settings", "Close the message, connect to trusted power and open the device's official update screen.", "the installed version, update source and basic functions tested afterward", "the update completes from settings and the normal task still works", "Stop if the update requests payment, remote access or credentials in an unfamiliar page.", ("cisa_world", "apple_iphone")),
    "app-permissions": ("apps retain camera, microphone or location access without a current reason", "Review one permission category at a time with the parent and note which app function uses it.", "the permission changed, why it was needed and the test result", "the app's needed feature works with the smallest reasonable access", "Restore the prior setting if an essential feature fails; investigate unfamiliar apps before opening them.", ("apple_iphone", "google_android")),
    "subscription-audit": ("recurring charges continue after the family stops using a service", "Open the official Apple, Google or service billing screen and match charges without sharing payment details.", "service name, renewal date, owner and cancellation confirmation", "each retained subscription has a named user and purpose", "Do not cancel storage, communication or safety-related services until data and replacement access are confirmed.", ("apple_subscriptions", "google_subscriptions")),
    "charging-battery-safety": ("a cable, charger or battery becomes damaged, swollen or unusually hot", "Move charging to a hard open surface and inspect cables and devices while they are cool and unplugged.", "the device model, charger used and any heat, swelling or damage observed", "normal charging stays cool enough to touch and uses undamaged equipment", "Stop using and move away from a swelling, smoking, leaking or rapidly heating battery; follow local emergency guidance.", ("cpsc_batteries", "cpsc_recalls")),
    "current-cpsc-recall": ("the household needs a model inventory before a future recall can be matched accurately", "Photograph or transcribe the maker, model and serial location without posting the serial publicly.", "the exact product name, model and official recall search date", "the family can confirm whether every identifying field matches a CPSC notice", "Stop using the product only when the official notice instructs it and the model matches; follow the listed remedy exactly.", ("cpsc_recalls", "cpsc_batteries")),
    "shared-calendar": ("appointments and family tech tasks are split across private calendars", "Choose one calendar owner and one low-risk test event before inviting anyone.", "the calendar owner, invited helpers and reminder time", "the parent receives and recognizes one test reminder", "Do not place passwords, access codes, medical details or private account notes in event text.", ("apple_iphone", "google_android")),
    "support-handoff": ("a second helper takes over without knowing what was tried or what must remain private", "Ask the parent to approve the new helper and summarize only the current task and safe history.", "device, symptom, completed tests and official support route", "the new helper can explain the next step before touching the device", "Stop if identity is uncertain or the handoff requires sending credentials, codes or unrestricted remote access.", ("ftc_support", "cisa_phishing")),
    "travel-away-checklist": ("a parent or caregiver will be away from the usual charger, network and nearby helper", "Test charging, calls, recovery and one offline contact card several days before departure.", "charger packed, backup contact, recovery route and support numbers available offline", "the traveler completes a call and finds the contact plan without coaching", "Do not make major account, phone-number or device changes immediately before travel.", ("ready_plan", "cisa_world")),
    "device-retirement": ("an old phone, tablet or computer still contains accounts and family files", "Back up approved files and list accounts that still recognize the device before signing out.", "backup location, sign-outs completed and erase confirmation", "the retained device can open needed files and the retired device no longer appears as trusted", "Do not donate, recycle or trade in the device until backup and account removal are independently verified.", ("epa_recycle", "cisa_world")),
    "annual-family-need": ("the family has several recurring technology frustrations but cannot fix everything at once", "Ask the parent which single problem causes the most repeated help and observe one normal attempt.", "the chosen problem, current workaround and one reversible improvement", "the selected task becomes easier without creating a new dependency", "Stop expanding the session after the agreed problem is solved; schedule unrelated work separately.", ("cisa_world", "ready_plan")),
    "password-manager": ("the family wants recoverable accounts without creating a shared paper password list", "Choose the official password-manager app and review recovery options with the account owner before importing anything.", "the app used, recovery method and who can help without knowing the master password", "the owner can unlock the manager and recover access through the approved route", "Do not share the master password, export an unprotected vault or appoint a helper without consent.", ("cisa_passwords", "google_recovery")),
    "two-factor-authentication": ("an account depends on one phone for every sign-in and recovery attempt", "Open the account's official security settings and identify the existing recovery route before adding a factor.", "the factor type, backup method and date both were tested", "the owner can sign in and can explain what happens if the phone is unavailable", "Stop if setup would remove the only working recovery method or asks for a code outside the official screen.", ("cisa_mfa", "cisa_passwords")),
    "phone-number-change": ("important accounts still send recovery messages to an old phone number", "List high-priority accounts from their official settings and keep both numbers active during the transition.", "which accounts were updated and which recovery tests passed", "the new number receives a test while the old route remains available", "Do not release the old number until banking, email and primary account recovery have been verified.", ("cisa_mfa", "google_recovery")),
    "family-tech-binder": ("helpers need a shared operating guide without creating a collection of family secrets", "Choose a binder location and define what is safe to record: device ownership, procedures and official support routes.", "device owner, trusted helper, safe procedure and last review date", "another approved helper can follow one routine without receiving credentials", "Never store passwords, one-time codes, full account numbers, medical records or door codes in the binder.", ("ready_plan", "cisa_world")),
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def sentence_action(value: str) -> str:
    value = value.strip().rstrip(".")
    return value[:1].lower() + value[1:]


def source_records(keys: tuple[str, str]) -> list[dict[str, str]]:
    return [{"name": SOURCES[key][0], "url": SOURCES[key][1]} for key in keys]


def render_guide(topic: dict[str, object]) -> str:
    slug = str(topic["topic_id"])
    scenario, prep, evidence, success, stop, source_keys = DETAILS[slug]
    title = str(topic["title"])
    question = str(topic["primary_question"])
    positioning = str(topic["positioning"])
    actions = [str(item) for item in topic["actions"]]
    sources = source_records(source_keys)
    canonical = f"https://parenttechchecklist.com/guides/{slug}"
    image = f"https://parenttechchecklist.com/assets/guides/{slug}.jpg"
    metadata = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": positioning,
        "image": [image],
        "datePublished": "2026-07-18",
        "dateModified": REVIEWED_AT,
        "mainEntityOfPage": canonical,
        "author": {"@type": "Organization", "name": "Parent Tech Checklist"},
        "reviewedBy": {"@type": "Organization", "name": EDITOR},
        "publisher": {"@type": "Organization", "name": "Parent Tech Checklist", "url": "https://parenttechchecklist.com"},
    }
    step_copy = [
        f"Begin with the parent beside you and {sentence_action(actions[0])}. For {title.lower()}, record {evidence}; keep passwords, recovery codes and private answers off the worksheet. The checkpoint is simple: {success}.",
        f"Next, {sentence_action(actions[1])}. For {title.lower()}, compare what appears on the device with the official guidance below, not with instructions from an incoming message or caller. {stop}",
        f"Finish by {sentence_action(actions[2])}. Ask the parent to repeat the result without coaching, then add the date beside {evidence}. If the {title.lower()} task cannot be repeated, return to the last working state and use the official support route.",
    ]
    source_html = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener">{esc(source["name"])}</a><span>Primary guidance used to review {esc(title)}.</span></li>'
        for source in sources
    )
    steps_html = "".join(
        f"<h3>{index}. {esc(action)}</h3><p>{esc(copy)}</p>"
        for index, (action, copy) in enumerate(zip(actions, step_copy), 1)
    )
    checklist = [question, *actions, f"We recorded {evidence}.", "The account owner understood every change.", "We tested one normal task after the change."]
    checklist_html = "".join(f'<li><span class="check-box" aria-hidden="true"></span>{esc(item)}</li>' for item in checklist)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{esc(title)} | Parent Tech Checklist</title>
  <meta name="description" content="{esc(positioning)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(positioning)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(image)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/png" href="/assets/ptc-avatar-96.png">
  <link rel="stylesheet" href="/styles.css?v=20260802-system">
  <link rel="stylesheet" href="/weekly-guides.css?v=20260802-system">
  <script type="application/ld+json">{json.dumps(metadata, ensure_ascii=True)}</script>
</head>
<body class="weekly-guide-page">
  <header class="site-header">
    <a class="brand" href="/" aria-label="Parent Tech Checklist home"><img src="/assets/ptc-avatar-96.png" width="42" height="42" alt="" decoding="async"><span>Parent Tech Checklist</span></a>
    <nav aria-label="Main navigation"><a href="/checklists/">Checklists</a><a href="/status/">Status</a><a href="/live/">Live</a><a href="/about">About</a></nav>
  </header>
  <main>
    <section class="guide-hero">
      <div><p class="eyebrow">Week {topic['week']} · {esc(topic['pillar'])}</p><h1>{esc(title)}</h1><p class="guide-question">{esc(question)}</p><p>{esc(positioning)}</p><div class="guide-actions"><a class="button primary" href="#family-checklist">Open the checklist</a><a class="button secondary" href="/live/?utm_source=weekly-guide&amp;utm_medium=internal&amp;utm_campaign=ptc-week{topic['week']}-{esc(slug)}">Watch official status</a></div></div>
      <img src="/assets/guides/{esc(slug)}.jpg" width="1280" height="720" alt="{esc(title)} guide thumbnail" decoding="async" fetchpriority="high">
    </section>
    <article class="guide-article">
      <div class="editorial-meta"><span>Reviewed {REVIEWED_AT}</span><span>By {EDITOR}</span><span>General technology education</span></div>
      <h2>The family question</h2>
      <p>{esc(question)} {esc(positioning)} This guide is for a household where {esc(scenario)}. For {esc(title)}, the goal is one repeatable task the account owner understands, not a broad device overhaul.</p>
      <h2>Before you begin</h2>
      <p>{esc(prep)} Before changing anything for {esc(title)}, agree on the exact result and keep a working contact method available in case the task needs to pause.</p>
      <h2>Three safe steps</h2>
      {steps_html}
      <h2>If it does not go as expected</h2>
      <p>{esc(stop)} While working on {esc(title)}, a warning, unfamiliar login screen or unexpected request for private information is a reason to pause, document what is visible and return through an official support page.</p>
      <h2>Make the family handoff clear</h2>
      <p>Write down {esc(evidence)} and the name of the approved helper. The {esc(title)} handoff is complete only when {esc(success)}. Review this topic note after a relevant device, account or caregiver change.</p>
      <h2 id="family-checklist">Printable family checklist</h2>
      <ul class="printable-checklist">{checklist_html}</ul>
      <h2>Official sources</h2>
      <p>Product screens change. For {esc(title)}, open these primary sources directly and verify that the instructions still match the device before acting.</p>
      <ul class="official-source-list">{source_html}</ul>
      <aside class="editorial-note" aria-label="Editorial process"><strong>How {esc(title)} was prepared</strong><p>Parent Tech Checklist used an assisted drafting workflow to organize this topic. The editorial desk reviewed the {esc(title)} steps, safety limits and official links on {REVIEWED_AT}. This topic revision replaced repeated copy with instructions and stop conditions specific to {esc(title)}.</p><a href="/editorial-method">Read the editorial method</a> · <a href="/corrections">Request a correction</a></aside>
      <h2>Safety boundary</h2>
      <p>This {esc(title)} checklist is general technology education for families, not medical, legal, financial, security or emergency advice. If an active outage, recall, scam notice or security advisory affects this topic, use the current official source and follow its stated instructions.</p>
    </article>
    <nav class="guide-footer-actions" aria-label="More Parent Tech resources"><a href="/checklists/">Browse all 40 weekly guides</a><a href="/status/">Open verified status</a><a href="/">Parent Tech Checklist home</a></nav>
  </main>
  <footer class="site-footer"><p>Parent Tech Checklist. Practical tech for aging parents and the families who care for them.</p><div class="footer-links"><a href="/about">About</a><a href="/editorial-method">Editorial method</a><a href="/corrections">Corrections</a></div></footer>
</body>
</html>
'''


def render_catalog(topics: list[dict[str, object]]) -> str:
    cards = []
    for topic in topics:
        search = " ".join([str(topic["title"]), str(topic["primary_question"]), str(topic["pillar"]), *topic["actions"]])
        cards.append(f'''<a class="catalog-card" href="{esc(topic['companion_path'])}" data-week="{topic['week']}" data-pillar="{esc(topic['pillar'])}" data-search="{esc(search.lower())}">
          <img src="{esc(topic['thumbnail_public_path'])}" srcset="{esc(topic['thumbnail_public_path']).replace('.jpg', '-480.webp')} 480w, {esc(topic['thumbnail_public_path']).replace('.jpg', '-720.webp')} 720w, {esc(topic['thumbnail_public_path'])} 1280w" sizes="(max-width: 620px) calc(100vw - 28px), (max-width: 980px) 50vw, 33vw" width="1280" height="720" alt="" loading="lazy" decoding="async">
          <span>Week {topic['week']} · {esc(topic['pillar'])}</span><h2>{esc(topic['title'])}</h2><p>{esc(topic['positioning'])}</p></a>''')
    filters = ["All", "Account continuity", "Communication", "Scam defense", "Home network", "Devices and accessibility", "Smart home", "Maintenance", "Caregiver routines"]
    filter_buttons = "".join(f'<button type="button" class="catalog-filter" data-filter="{esc(value)}" aria-pressed="{str(value == "All").lower()}">{esc(value)}</button>' for value in filters)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>40-Week Family Tech Checklist Library</title>
  <meta name="description" content="Search 40 practical family technology checklists for aging parents by problem or topic.">
  <link rel="canonical" href="https://parenttechchecklist.com/checklists/">
  <meta property="og:title" content="40 Weeks of Calm Family Tech Checklists"><meta property="og:description" content="Find the family technology problem you need to solve now."><meta property="og:image" content="https://parenttechchecklist.com/assets/guides/password-recovery.jpg">
  <link rel="icon" type="image/png" href="/assets/ptc-avatar-96.png">
  <link rel="stylesheet" href="/styles.css?v=20260802-system"><link rel="stylesheet" href="/weekly-guides.css?v=20260802-system">
</head>
<body class="weekly-catalog-page">
  <header class="site-header"><a class="brand" href="/"><img src="/assets/ptc-avatar-96.png" width="42" height="42" alt=""><span>Parent Tech Checklist</span></a><nav aria-label="Main navigation"><a href="/checklists/">Checklists</a><a href="/status/">Status</a><a href="/live/">Live</a><a href="/about">About</a></nav></header>
  <main>
    <section class="catalog-hero"><p class="eyebrow">Complete family resource library</p><h1>Find the right family tech checklist</h1><p>Start with the problem happening today. Search all 40 weeks or choose a familiar family need.</p><div class="catalog-search"><label for="guide-search">What does your family need help with?</label><input id="guide-search" type="search" placeholder="Try password, scam, Wi-Fi, calls or smart home" autocomplete="off"></div></section>
    <section class="catalog-current" aria-labelledby="current-guide-title"><p class="eyebrow">This week's calm next step</p><h2 id="current-guide-title">Password Recovery Without Panic</h2><p id="current-guide-copy">Create a recovery plan before a lockout, using official recovery paths and trusted contact methods.</p><a id="current-guide-link" class="button primary" href="/guides/password-recovery">Open this week's guide</a></section>
    <section class="catalog-tools" aria-label="Filter guides"><h2>Choose a family need</h2><div class="catalog-filters">{filter_buttons}</div><p id="catalog-result-count" role="status" aria-live="polite">Showing 6 recommended guides. Search or choose a topic for more.</p></section>
    <section><div id="catalog-grid" class="catalog-grid catalog-collapsed">{''.join(cards)}</div><div class="catalog-more"><button id="show-all-guides" type="button" class="button secondary">Show all 40 guides</button></div></section>
    <section class="catalog-existing"><h2>Core buying and setup guides</h2><div class="catalog-grid compact-grid"><a class="catalog-card compact" href="/guides/senior-phones"><span>Phone basics</span><h2>Best Phones for Seniors</h2></a><a class="catalog-card compact" href="/guides/scam-call-safety"><span>Scam defense</span><h2>Scam and Call Safety</h2></a><a class="catalog-card compact" href="/guides/video-calling"><span>Communication</span><h2>Video Calling Devices</h2></a><a class="catalog-card compact" href="/guides/living-alone-safety"><span>Living alone</span><h2>Living Alone Safety Tech</h2></a><a class="catalog-card compact" href="/guides/medication-reminders"><span>Caregiver routines</span><h2>Medication Reminders</h2></a></div></section>
  </main>
  <footer class="site-footer"><p>General technology education only. Never post passwords, codes, private account details, medical information, addresses or emergency contacts.</p><div class="footer-links"><a href="/about">About</a><a href="/editorial-method">Editorial method</a><a href="/corrections">Corrections</a></div></footer>
  <script src="/assets/checklists.js?v=20260802-system" defer></script>
</body></html>'''


def render_sitemap(topics: list[dict[str, object]]) -> str:
    static_paths = ["/", "/status/", "/live/", "/checklists/", "/guides/7-day-parent-tech-setup", "/guides/senior-phones", "/guides/scam-call-safety", "/guides/video-calling", "/guides/living-alone-safety", "/guides/medication-reminders", "/products/parent-tech-quick-start-kit", "/products/personalized-setup-review", "/about", "/editorial-method", "/corrections", "/contact", "/privacy", "/disclosure"]
    paths = static_paths + [str(topic["companion_path"]) for topic in topics]
    rows = "\n".join(f"  <url><loc>https://parenttechchecklist.com{path}</loc><lastmod>{REVIEWED_AT}</lastmod></url>" for path in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n'


def visible_word_count(markup: str) -> int:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", markup, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return len(re.findall(r"\b[\w'-]+\b", html.unescape(text)))


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    topics = manifest["topics"]
    if len(topics) != 40 or set(DETAILS) != {topic["topic_id"] for topic in topics}:
        raise SystemExit("Weekly detail registry does not match the 40-topic manifest")
    for topic in topics:
        if topic["topic_id"] == "family-tech-binder":
            topic["title"] = "Build a Family Tech Binder"
            topic["primary_question"] = "Can another trusted helper follow the plan without receiving passwords or codes?"
            topic["positioning"] = "Create a safe family handoff guide for devices, helpers and official support routes."
        topic["reviewed_at"] = REVIEWED_AT
        topic["reviewed_by"] = EDITOR
        topic["update_reason"] = "Rewritten with topic-specific steps, stop conditions and primary official sources."
        topic["sources"] = source_records(DETAILS[topic["topic_id"]][-1])
        guide = render_guide(topic)
        topic["word_count"] = visible_word_count(guide)
        (SITE_DIR / "guides" / f"{topic['topic_id']}.html").write_text(guide, encoding="utf-8")
    manifest["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["editorial_revision"] = "people_first_sources_v1"
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (SITE_DIR / "checklists" / "index.html").write_text(render_catalog(topics), encoding="utf-8")
    (SITE_DIR / "sitemap.xml").write_text(render_sitemap(topics), encoding="utf-8")
    print(json.dumps({"guides": len(topics), "reviewed_at": REVIEWED_AT, "min_words": min(t["word_count"] for t in topics), "max_words": max(t["word_count"] for t in topics)}))


if __name__ == "__main__":
    main()
