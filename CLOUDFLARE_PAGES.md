# Cloudflare Pages Deployment Notes

This site is Cloudflare Pages-ready as a static HTML project.

## Recommended Setup Before Domain Decision

- Production source: keep GitHub Pages at `https://arthur0858.github.io/ynk-blog/`.
- Cloudflare Pages: create as staging or preview only.
- Build command: leave blank.
- Build output directory: `/` or project root.
- Canonical URLs: keep pointing to GitHub Pages until the final domain is chosen.
- Do not add redirects from GitHub Pages or `pages.dev` until the final domain is selected.

## Included Files

- `_headers`: conservative security headers and cache rules for Cloudflare Pages.
- `404.html`: static not-found page.
- `robots.txt`: currently points search engines to the GitHub Pages sitemap.
- `sitemap.xml`: currently uses GitHub Pages URLs.

## Before Final Domain Cutover

1. Choose the final domain.
2. Add the domain to Cloudflare and verify DNS.
3. Update canonical URLs, OG URLs, sitemap, robots sitemap URL, and 404 links.
4. Update YouTube descriptions only after the final production URL is stable.
5. Update affiliate network website/profile URLs if required by each network.
6. Add redirects only after the final domain is live and verified.

## Compliance Reminder

No unapproved affiliate links should be published. Safety, medical, emergency, and scam copy must stay comparison-focused and avoid guarantee claims.
