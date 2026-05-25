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

Current deployment uses a local direct-upload script instead of the Cloudflare dashboard UI.

### One-time prerequisite

Install the asset hash dependency on the machine that will deploy:

```bash
python3 -m pip install --user blake3
```

### Scripted production deploy

From the `site/` repo root, run:

```bash
python3 scripts/deploy_cloudflare_pages.py
```

Helpful variants:

```bash
python3 scripts/deploy_cloudflare_pages.py --dry-run
python3 scripts/deploy_cloudflare_pages.py --verify-aliases
python3 scripts/deploy_cloudflare_pages.py --skip-caching
```

### What the script does

1. Reads the Cloudflare Pages write token from `~/.config/parenttechchecklist/cloudflare-pages-write.token` unless `CLOUDFLARE_API_TOKEN` is set.
2. Uses the current git repo to attach `commit_hash`, `commit_message`, and `commit_dirty`.
3. Uploads only missing static assets by calling the same Pages direct-upload APIs used by Wrangler.
4. Re-attaches `_headers` and `_redirects` on every deployment.
5. Polls until the Pages deployment reaches `success`.
6. Verifies the deployment URL by checking `/`, `/products/parent-tech-quick-start-kit`, `/robots.txt`, and `/sitemap.xml`.

### Deployment scope and exclusions

The script is intentionally static-site only for this project. It does not bundle Pages Functions or `_worker.js`.

It excludes these local-only inputs from public deployment:

- `.git/`, `.wrangler/`, `functions/`, `node_modules/`, `scripts/`
- hidden files such as `.DS_Store`
- Markdown and local docs such as `CLOUDFLARE_PAGES.md` and `DESIGN.md`

### Post-deploy checks

After deployment, confirm:

1. Live HTML still points YouTube traffic to `https://www.youtube.com/@ParentTechChecklist`.
2. `.html` guide URLs return 301 to extensionless URLs.
3. `https://www.parenttechchecklist.com/` returns 301 to `https://parenttechchecklist.com/` after adding a Cloudflare Redirect Rule or Bulk Redirect.
4. Affiliate network website/profile URLs remain current where required.

## Compliance Reminder

No unapproved affiliate links should be published. Safety, medical, emergency, and scam copy must stay comparison-focused and avoid guarantee claims.
