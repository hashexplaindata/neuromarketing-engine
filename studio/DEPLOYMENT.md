# Neuromarketing Studio React Studio Deployment

The React Studio is a Vite static application. It can be staged on GitHub Pages, Cloudflare Pages, Netlify, or another static host, while the authenticated API remains on Heroku. Set `VITE_API_BASE_URL` to the Heroku API URL at build time and configure the API’s `CORS_ORIGINS` to the exact deployed Studio origin.

## Controlled-pilot limitation

The current pilot client accepts `VITE_ACCESS_TOKEN` at build time because the inherited backend contract supports signed pilot tokens and Appwrite JWT verification. **Do not publish a build containing a long-lived shared token.** For an external commercial launch, replace this mechanism with Appwrite Web Auth or OAuth in the browser, create a short-lived Appwrite JWT after login, and keep only the short-lived token in memory. This is a release gate, not a capability to hide.

## Local/staging build

```bash
cd studio
VITE_API_BASE_URL=https://neuromarketing-suite-eb8efca8edd1.herokuapp.com \
VITE_ACCESS_TOKEN='<short-lived pilot token>' \
./node_modules/.bin/tsc --noEmit && ./node_modules/.bin/vite build
```

The resulting `studio/dist` directory is the static artifact. Never commit `.env`, service keys, Modal tokens, Appwrite API keys, Gemini keys, or long-lived JWTs.

## API CORS configuration

On Heroku, set `CORS_ORIGINS` to a comma-separated allowlist containing the exact Studio origin and any approved local development origins. Do not use `*` with credentials in production.

## Required commercial-authentication gate

Before public customer access, implement browser authentication using Appwrite Account sessions or an approved identity provider. The client must obtain a user-scoped JWT only after login; the API must validate that JWT and derive the tenant from the verified Appwrite user/team context. Shared build-time tokens are acceptable only for internal staging and must be rotated after a pilot.
