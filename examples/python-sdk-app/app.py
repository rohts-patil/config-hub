from __future__ import annotations

import atexit
import json
import os
from html import escape
from typing import Optional
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from confighub_sdk import ConfigHubClient

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PORT = 5050
DEFAULT_POLL_INTERVAL_SECONDS = 30

_client: Optional[ConfigHubClient] = None


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing {name}. Set it before starting the sample app."
        )
    return value


def get_client() -> ConfigHubClient:
    global _client
    if _client is not None:
        return _client

    sdk_key = get_required_env("CONFIGHUB_SDK_KEY")
    base_url = os.environ.get("CONFIGHUB_BASE_URL", DEFAULT_BASE_URL).strip()
    poll_interval = int(
        os.environ.get(
            "CONFIGHUB_POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS)
        )
    )

    _client = ConfigHubClient.create(
        sdk_key,
        base_url=base_url,
        poll_interval_seconds=poll_interval,
    )
    atexit.register(_client.destroy)
    return _client


def get_user(query: dict[str, list[str]]) -> dict[str, str]:
    return {
        "identifier": query.get("identifier", ["demo-user-123"])[0],
        "country": query.get("country", ["IN"])[0],
        "plan": query.get("plan", ["free"])[0],
    }


def get_example_values(
    client: ConfigHubClient, user: dict[str, str]
) -> dict[str, object]:
    return {
        "new_dashboard": client.get_value("new_dashboard", False, user),
        "welcome_message": client.get_value(
            "welcome_message",
            "Hello from the Python sample app",
            user,
        ),
        "checkout_theme": client.get_value("checkout_theme", "classic", user),
    }


def json_response(start_response, status: str, payload: dict[str, object]):
    body = json.dumps(payload, indent=2).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def html_response(start_response, status: str, html: str):
    body = html.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def render_home_page(
    user: dict[str, str],
    all_values: dict[str, object],
    example_values: dict[str, object],
    base_url: str,
) -> str:
    all_flags_json = escape(json.dumps(all_values, indent=2, sort_keys=True))
    example_rows = "".join(
        f"""
        <tr>
          <td>{escape(key)}</td>
          <td><code>{escape(json.dumps(value))}</code></td>
        </tr>
        """
        for key, value in example_values.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ConfigHub Python SDK Sample</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f5efe8;
        --card: #fffdf9;
        --text: #2f241d;
        --muted: #78665c;
        --accent: #c86b34;
        --border: #e6d8cd;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        font-family: "Georgia", "Times New Roman", serif;
        background:
          radial-gradient(circle at top left, rgba(200, 107, 52, 0.18), transparent 30%),
          linear-gradient(180deg, #fbf7f2 0%, var(--bg) 100%);
        color: var(--text);
      }}
      main {{
        max-width: 980px;
        margin: 0 auto;
        padding: 40px 20px 56px;
      }}
      .hero {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 24px 80px rgba(67, 40, 24, 0.08);
      }}
      .eyebrow {{
        margin: 0 0 10px;
        color: var(--accent);
        font-size: 12px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }}
      h1 {{
        margin: 0 0 10px;
        font-size: clamp(2rem, 5vw, 3.6rem);
        line-height: 1.05;
      }}
      p {{
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }}
      .grid {{
        display: grid;
        gap: 20px;
        margin-top: 24px;
      }}
      @media (min-width: 860px) {{
        .grid {{
          grid-template-columns: 1.2fr 0.8fr;
        }}
      }}
      .card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 22px;
      }}
      .stack {{
        display: grid;
        gap: 10px;
      }}
      .pill-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }}
      .pill {{
        padding: 10px 14px;
        border: 1px solid var(--border);
        border-radius: 999px;
        background: rgba(200, 107, 52, 0.06);
        font-size: 14px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      th,
      td {{
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
        text-align: left;
        vertical-align: top;
      }}
      th {{
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      code,
      pre {{
        font-family: "SFMono-Regular", "Menlo", monospace;
      }}
      pre {{
        margin: 0;
        padding: 16px;
        overflow: auto;
        background: #241a15;
        color: #f6ede5;
        border-radius: 16px;
        font-size: 13px;
      }}
      .footer {{
        margin-top: 22px;
        font-size: 14px;
        color: var(--muted);
      }}
      a {{
        color: var(--accent);
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">ConfigHub SDK Demo</p>
        <h1>Python app with live feature flag evaluation.</h1>
        <p>
          This sample app fetches <code>config.json</code> from
          <code>{escape(base_url)}</code>, evaluates flags for a demo user, and
          renders both targeted example values and the full resolved flag map.
        </p>
        <div class="pill-row">
          <div class="pill">identifier: <strong>{escape(user["identifier"])}</strong></div>
          <div class="pill">country: <strong>{escape(user["country"])}</strong></div>
          <div class="pill">plan: <strong>{escape(user["plan"])}</strong></div>
        </div>
      </section>

      <section class="grid">
        <article class="card">
          <div class="stack">
            <h2>Example evaluations</h2>
            <p>
              These use <code>client.get_value(...)</code> with fallback values.
            </p>
          </div>
          <table>
            <thead>
              <tr>
                <th>Flag Key</th>
                <th>Resolved Value</th>
              </tr>
            </thead>
            <tbody>
              {example_rows}
            </tbody>
          </table>
        </article>

        <article class="card">
          <div class="stack">
            <h2>Try different users</h2>
            <p>
              Change the query string to simulate targeting:
              <code>?identifier=alice&country=US&plan=pro</code>
            </p>
            <p>
              JSON endpoint:
              <a href="/api/flags?identifier={escape(user["identifier"])}&country={escape(user["country"])}&plan={escape(user["plan"])}">
                /api/flags
              </a>
            </p>
          </div>
        </article>
      </section>

      <section class="card" style="margin-top: 20px;">
        <div class="stack">
          <h2>All resolved values</h2>
          <p>
            This uses <code>client.get_all_values(user)</code>.
          </p>
        </div>
        <pre>{all_flags_json}</pre>
      </section>

      <p class="footer">
        Tip: create a few flags in ConfigHub, attach them to the SDK key you use here,
        and refresh this page to see the values update.
      </p>
    </main>
  </body>
</html>
"""


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    query = parse_qs(environ.get("QUERY_STRING", ""))
    user = get_user(query)
    base_url = os.environ.get("CONFIGHUB_BASE_URL", DEFAULT_BASE_URL).strip()

    try:
        client = get_client()
    except Exception as exc:
        payload = {
            "error": str(exc),
            "hint": "Set CONFIGHUB_SDK_KEY before starting the sample app.",
        }
        return json_response(start_response, "500 Internal Server Error", payload)

    if path == "/health":
        return json_response(
            start_response,
            "200 OK",
            {"status": "ok", "sdk_connected": client.get_config() is not None},
        )

    if path == "/api/flags":
        all_values = client.get_all_values(user)
        example_values = get_example_values(client, user)
        return json_response(
            start_response,
            "200 OK",
            {
                "user": user,
                "example_values": example_values,
                "all_values": all_values,
            },
        )

    if path != "/":
        return json_response(
            start_response,
            "404 Not Found",
            {"error": "Not found"},
        )

    all_values = client.get_all_values(user)
    example_values = get_example_values(client, user)
    html = render_home_page(user, all_values, example_values, base_url)
    return html_response(start_response, "200 OK", html)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    print(f"ConfigHub Python SDK sample running at http://localhost:{port}")
    with make_server("0.0.0.0", port, application) as server:
        server.serve_forever()
