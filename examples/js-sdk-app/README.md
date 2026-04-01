# JavaScript SDK Sample App

Tiny demo app showing how to integrate the ConfigHub JavaScript SDK into a Node
application.

## What it does

- creates a `ConfigHubClient`
- fetches `config.json` from your ConfigHub backend
- evaluates a few named example flags with fallbacks
- exposes a JSON endpoint with all resolved values for a user

## Setup

Build the SDK first from the repo root:

```bash
cd packages/sdk-js
npm install
npm run build
```

Then start the sample app:

```bash
cd ../../examples/js-sdk-app
export CONFIGHUB_SDK_KEY=YOUR_SDK_KEY
export CONFIGHUB_BASE_URL=http://localhost:8000
npm start
```

Open:

- `http://localhost:5051/`
- `http://localhost:5051/api/flags`
- `http://localhost:5051/health`

## Try targeting

You can simulate different users with query params:

```text
http://localhost:5051/?identifier=alice&country=US&plan=pro
http://localhost:5051/api/flags?identifier=bob&country=IN&plan=free
```

## Expected env vars

- `CONFIGHUB_SDK_KEY`: required
- `CONFIGHUB_BASE_URL`: optional, defaults to `http://localhost:8000`
- `CONFIGHUB_POLL_INTERVAL_SECONDS`: optional, defaults to `30`
- `PORT`: optional, defaults to `5051`

## Notes

- The example flag keys are `new_dashboard`, `welcome_message`, and
  `checkout_theme`.
- If those flags do not exist in your project yet, the sample app will just
  show the fallback values.
