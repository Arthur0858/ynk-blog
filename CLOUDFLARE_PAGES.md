# Cloudflare Pages Deployment Notes

This site is deployed on Cloudflare Pages as a static HTML project.

## Current Production Setup

- Production domain: `https://parenttechchecklist.com/`.
- Cloudflare Pages project: `parenttechchecklist`.
- Pages preview URL: `https://parenttechchecklist.pages.dev/`.
- Secondary custom domain: `https://www.parenttechchecklist.com/`.
- Build command: leave blank.
- Build output directory: `/` or project root.
- Canonical URLs: use `https://parenttechchecklist.com/`.
- Custom domains added: `parenttechchecklist.com` and `www.parenttechchecklist.com`.
- `www.parenttechchecklist.com` is live. Direct-upload Pages deployments do not execute `functions/_middleware.js`, and `_redirects` does not reliably apply host-level redirects on custom domains. Add a Cloudflare Redirect Rule or Bulk Redirect for `www` to apex.
- The retired GitHub Pages deployment has been unpublished and disabled. Do not use retired GitHub Pages URLs in public copy.

## Included Files

- `_headers`: conservative security headers and cache rules for Cloudflare Pages.
- `_redirects`: `.html` guide URLs redirect to extensionless URLs; `www` is intended to redirect to the apex domain.
- `404.html`: static not-found page.
- `robots.txt`: points search engines to the production sitemap.
- `sitemap.xml`: uses production domain URLs.
- `contact.html`, `privacy.html`, and `disclosure.html`: trust and compliance pages for users and affiliate review.

## Deployment Workflow

Current deployment is manual direct upload through the Cloudflare dashboard because local GitHub push credentials are unavailable.

1. Prepare the upload folder from `site/`, excluding `.git`, `.DS_Store`, `CLOUDFLARE_PAGES.md`, and `DESIGN.md`.
2. Upload the prepared folder to the Cloudflare Pages project `parenttechchecklist`.
3. Select the Production environment.
4. Verify `/`, `/guides/senior-phones`, `/contact`, `/privacy`, `/disclosure`, `/robots.txt`, and `/sitemap.xml`.
5. Confirm live HTML points YouTube traffic to `https://www.youtube.com/@ParentTechChecklist`.
6. Confirm `.html` guide URLs return 301 to extensionless URLs.
7. Confirm `https://www.parenttechchecklist.com/` returns 301 to `https://parenttechchecklist.com/` after adding a Cloudflare Redirect Rule or Bulk Redirect.
8. Update affiliate network website/profile URLs if required by each network.

When GitHub credentials are fixed, connect or push the repo and use Cloudflare Pages Git deploys instead of manual uploads.

## Compliance Reminder

No unapproved affiliate links should be published. Safety, medical, emergency, and scam copy must stay comparison-focused and avoid guarantee claims.
