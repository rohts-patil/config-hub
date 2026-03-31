# Python SDK Sample App

Tiny demo app showing how to integrate the ConfigHub Python SDK into a Python
application.

## What it does

- creates a `ConfigHubClient`
- fetches `config.json` from your ConfigHub backend
- evaluates a few named example flags with fallbacks
- exposes a JSON endpoint with all resolved values for a user

## Setup

From the repo root:

```bash
cd packages/sdk-python
pip install -e .
```

Then start the sample app:

```bash
cd ../../examples/python-sdk-app
export CONFIGHUB_SDK_KEY=YOUR_SDK_KEY
export CONFIGHUB_BASE_URL=http://localhost:8000
python3 app.py
```

Open:

- `http://localhost:5050/`
- `http://localhost:5050/api/flags`
- `http://localhost:5050/health`

## Try targeting

You can simulate different users with query params:

```text
http://localhost:5050/?identifier=alice&country=US&plan=pro
http://localhost:5050/api/flags?identifier=bob&country=IN&plan=free
```

## Expected env vars

- `CONFIGHUB_SDK_KEY`: required
- `CONFIGHUB_BASE_URL`: optional, defaults to `http://localhost:8000`
- `CONFIGHUB_POLL_INTERVAL_SECONDS`: optional, defaults to `30`
- `PORT`: optional, defaults to `5050`

## Notes

- The example flag keys are `new_dashboard`, `welcome_message`, and
  `checkout_theme`.
- If those flags do not exist in your project yet, the sample app will just
  show the fallback values.
