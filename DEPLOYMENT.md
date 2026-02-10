# Deployment Instructions

This site is deployed to **Cloudflare Pages** using the Wrangler CLI.

## Prerequisites
- Node.js and npm installed.
- Cloudflare account with access to the `la-relocation` project.
- Wrangler authenticated (`npx wrangler login`).

## Deployment
To deploy the site to production:

```bash
npx wrangler pages deploy .
```

This command will:
1.  Upload the current directory contents to Cloudflare Pages.
2.  Use the project name `la-relocation` defined in `wrangler.toml`.
3.  Apply the middleware defined in `functions/_middleware.js`.

## Verification
After deployment:
1.  Wrangler will output a `*.pages.dev` URL.
2.  Visit the URL to confirm the site is live.
3.  Check for security headers using `curl -I <url>`.
