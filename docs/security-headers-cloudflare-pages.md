# Security headers: CSP + Connection Allowlist (Cloudflare Pages)

**Why.** GitHub Pages cannot set HTTP response headers, and Chrome's Connection
Allowlist (Chrome 152) works only as a header. The site has no CSP today either.
`_headers` in the repo root holds the ready policy; it works on Cloudflare Pages
or Netlify. GitHub Pages ignores it, so merging it changes nothing live.

**Why not just put Cloudflare in front of GitHub Pages.** Cloudflare's free plan
needs the whole zone `animacoffee.com.ua` moved to its nameservers. That touches
the client's main site and mail. Hosting the same repo on Cloudflare Pages needs
only one CNAME change for `aeo.animacoffee.com.ua`.

## 5 minutes (owner of DNS for animacoffee.com.ua does step 4)

1. Cloudflare dashboard -> Workers & Pages -> Create -> Pages -> Connect to Git ->
   `ADV-IT-Performance-Corp/anima-coffee-site`, branch `main`.
2. Build command: empty. Output directory: `/` (repo root, a static site).
3. Deploy. Check the `*.pages.dev` URL: `curl -sI https://<project>.pages.dev/ | grep -iE "content-security|connection-allow"`
   must show both `...-Report-Only` headers. Open the site with Chrome DevTools
   and read Console / Issues for violations.
4. Project -> Custom domains -> add `aeo.animacoffee.com.ua`. At the DNS provider of
   animacoffee.com.ua change the CNAME `aeo` from `adv-it-performance-corp.github.io`
   to `<project>.pages.dev`. Lower the TTL to 300 s beforehand for fast rollback.
5. Verify: home page loads, a lead form and the chat widget deliver a test lead to
   Roistat, GTM fires, `/robots.txt` and `/sitemap.xml` return 200.

**Rollback:** set the CNAME back to `adv-it-performance-corp.github.io`.

**Note:** merge to `main` deploys to Cloudflare Pages after the switch, as it does
on GitHub Pages now. Disable GitHub Pages only after the new host is verified.

## Enforcing later

After about a week without unexpected violations, rename
`Content-Security-Policy-Report-Only` to `Content-Security-Policy` and
`Connection-Allowlist-Report-Only` to `Connection-Allowlist`. If a live chat backend
(`anima-chat-ws` meta) or a lead endpoint (`data-endpoint`) is configured, add its
origin to `connect-src` and to the allowlist first, or leads and chat will break.
Redirects and WebRTC are blocked by default under the allowlist; the site uses neither.

**Caveat:** the Connection-Allowlist syntax follows the Chrome announcement
(structured-field inner list of URLPattern strings plus `response-origin`). It was not
tested in a live Chrome 152 from this environment; report-only mode makes a mistake safe.
CSP keeps `'unsafe-inline'` because the GTM snippet and style attributes are inline;
moving to nonces/hashes is a separate task.

## Deploy without connecting GitHub to Cloudflare (chosen 2026-10-31)

Cloudflare belongs to Anima, the repo to the agency, so Cloudflare is NOT given access to
GitHub. Instead `.github/workflows/deploy-cloudflare-pages.yml` pushes the site with an API token.

1. Cloudflare (Anima account) -> Workers & Pages -> Create -> Pages -> **Upload assets**,
   project name `anima-coffee-site`, upload any placeholder file once.
2. My Profile -> API Tokens -> Create Token -> Custom: permission **Account / Cloudflare Pages / Edit**,
   resource: Anima's account only. Copy the token. Copy the Account ID from the account home page.
3. GitHub repo -> Settings -> Secrets and variables -> Actions: add `CLOUDFLARE_API_TOKEN`
   and `CLOUDFLARE_ACCOUNT_ID`.
4. Actions -> deploy-cloudflare-pages -> Run workflow. Then continue from step 3 above
   (check the `pages.dev` URL) before touching DNS.

GitHub Actions in the org must be working for this (the gates currently fail within seconds).
