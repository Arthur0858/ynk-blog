# CTA measurement

The live and status pages use first-party redirect paths so Cloudflare request
analytics can distinguish CTA traffic without a browser analytics script,
cookies, or KV writes.

| Path | Meaning |
| --- | --- |
| `/go/live-youtube` | YouTube click from `/live/` |
| `/go/status-youtube` | YouTube click from `/status/` |
| `/go/home-live-youtube` | YouTube click from the home live band |
| `/go/medication-live-youtube` | YouTube live click from the medication reminder guide |
| `/go/live-senior-phone` | Senior phone checklist click from `/live/` |
| `/go/live-video-calling` | Video calling checklist click from `/live/` |
| `/go/live-scam-safety` | Scam safety checklist click from `/live/` |
| `/go/home-problem-communication` | Calls and video problem choice from home |
| `/go/home-problem-account` | Accounts and access problem choice from home |
| `/go/home-problem-scam` | Scams and messages problem choice from home |
| `/go/home-problem-network` | Wi-Fi and outage problem choice from home |
| `/go/home-problem-device` | Devices and settings problem choice from home |
| `/go/home-problem-caregiver` | Caregiver routines problem choice from home |

The privacy-first funnel is read as page requests, without cookies: landing page, one problem-choice redirect, a guide or product page, the local Gumroad handoff, then the Gumroad sale UTM. A handoff request does not prove a sale.

Measurement started with deployment `bcc42354` on 2026-07-17. Treat these as
request counts, not unique people. Filter known bots where the Cloudflare view
supports it, and do not combine the six paths into one conversion metric.

The home live-band path `/go/home-live-youtube` was added with deployment
`aae126fd` on 2026-07-17. Compare it only against traffic after that deployment;
earlier homepage visits had no equivalent direct-live CTA.

The medication guide path replaces a non-functional placeholder video URL. Its
request count starts with the deployment that first includes this route; do not
compare it with earlier guide traffic.

The website privacy policy remains accurate: no analytics script is loaded.
Cloudflare hosting and request logs are already disclosed under Hosting And
Logs.
