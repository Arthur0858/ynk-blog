# Cloudflare Pages Deployment Notes

This site is Cloudflare Pages-ready as a static HTML project.

## Recommended Setup After Domain Purchase

- Production domain: `https://parenttechchecklist.com/`.
- Cloudflare Pages: use as the production host once the GitHub repo is connected.
- Build command: leave blank.
- Build output directory: `/` or project root.
- Canonical URLs: use `https://parenttechchecklist.com/`.
- Add both apex and `www` custom domains if Cloudflare Pages asks for them.
- Redirect `www.parenttechchecklist.com` to `parenttechchecklist.com` with Cloudflare Bulk Redirects after both are live. Pages `_redirects` does not handle host-level redirects.

## Included Files

- `_headers`: conservative security headers and cache rules for Cloudflare Pages.
- `404.html`: static not-found page.
- `robots.txt`: points search engines to the production sitemap.
- `sitemap.xml`: uses production domain URLs.

## Final Domain Cutover

1. Create the Cloudflare Pages project from the GitHub repo.
2. Use no build command and the repository root as the output directory.
3. Add `parenttechchecklist.com` as the production custom domain.
4. Add `www.parenttechchecklist.com` if visitors may type the `www` version.
5. If a strict `www` to apex redirect is required, configure Cloudflare Bulk Redirects from `www.parenttechchecklist.com/*` to `https://parenttechchecklist.com/:splat` with a 301 status, preserving path suffix and query string.
6. Verify `/`, `/guides/senior-phones.html`, `/robots.txt`, and `/sitemap.xml`.
7. Update YouTube descriptions only after the final production URL is stable.
8. Update affiliate network website/profile URLs if required by each network.

## Compliance Reminder

No unapproved affiliate links should be published. Safety, medical, emergency, and scam copy must stay comparison-focused and avoid guarantee claims.
