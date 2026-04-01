"use strict";

const http = require("node:http");
const { URL } = require("node:url");

const DEFAULT_BASE_URL = "http://localhost:8000";
const DEFAULT_PORT = 5051;
const DEFAULT_POLL_INTERVAL_SECONDS = 30;

let client = null;

function loadSdk() {
  try {
    return require("../../packages/sdk-js/dist/index.js");
  } catch (error) {
    throw new Error(
      "ConfigHub JS SDK is not built yet. Run `cd packages/sdk-js && npm install && npm run build` first.",
    );
  }
}

function getRequiredEnv(name) {
  const value = (process.env[name] || "").trim();
  if (!value) {
    throw new Error(`Missing ${name}. Set it before starting the sample app.`);
  }
  return value;
}

async function getClient() {
  if (client) {
    return client;
  }

  const { ConfigHubClient } = loadSdk();
  const sdkKey = getRequiredEnv("CONFIGHUB_SDK_KEY");
  const baseUrl = (process.env.CONFIGHUB_BASE_URL || DEFAULT_BASE_URL).trim();
  const pollIntervalSeconds = Number.parseInt(
    process.env.CONFIGHUB_POLL_INTERVAL_SECONDS ||
      String(DEFAULT_POLL_INTERVAL_SECONDS),
    10,
  );

  client = await ConfigHubClient.create(sdkKey, {
    baseUrl,
    pollIntervalSeconds,
  });

  const cleanup = () => {
    if (client) {
      client.destroy();
      client = null;
    }
  };

  process.once("exit", cleanup);
  process.once("SIGINT", () => {
    cleanup();
    process.exit(0);
  });
  process.once("SIGTERM", () => {
    cleanup();
    process.exit(0);
  });

  return client;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getUser(searchParams) {
  return {
    identifier: searchParams.get("identifier") || "demo-user-123",
    country: searchParams.get("country") || "IN",
    plan: searchParams.get("plan") || "free",
  };
}

function getExampleValues(confighubClient, user) {
  return {
    new_dashboard: confighubClient.getValue("new_dashboard", false, user),
    welcome_message: confighubClient.getValue(
      "welcome_message",
      "Hello from the JavaScript sample app",
      user,
    ),
    checkout_theme: confighubClient.getValue("checkout_theme", "classic", user),
  };
}

function sendJson(res, statusCode, payload) {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function sendHtml(res, statusCode, html) {
  res.writeHead(statusCode, {
    "Content-Type": "text/html; charset=utf-8",
    "Content-Length": Buffer.byteLength(html),
  });
  res.end(html);
}

function renderHomePage(user, allValues, exampleValues, baseUrl) {
  const allFlagsJson = escapeHtml(JSON.stringify(allValues, null, 2));
  const exampleRows = Object.entries(exampleValues)
    .map(
      ([key, value]) => `
        <tr>
          <td>${escapeHtml(key)}</td>
          <td><code>${escapeHtml(JSON.stringify(value))}</code></td>
        </tr>
      `,
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ConfigHub JS SDK Sample</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #edf5ef;
        --card: #fbfffc;
        --text: #1f2e22;
        --muted: #5d7262;
        --accent: #1f8a5b;
        --border: #d4e4d8;
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(31, 138, 91, 0.16), transparent 32%),
          linear-gradient(180deg, #f7fbf8 0%, var(--bg) 100%);
        color: var(--text);
      }
      main {
        max-width: 980px;
        margin: 0 auto;
        padding: 40px 20px 56px;
      }
      .hero,
      .card {
        background: var(--card);
        border: 1px solid var(--border);
        box-shadow: 0 24px 80px rgba(23, 52, 31, 0.08);
      }
      .hero {
        border-radius: 26px;
        padding: 28px;
      }
      .card {
        border-radius: 20px;
        padding: 22px;
      }
      .eyebrow {
        margin: 0 0 10px;
        color: var(--accent);
        font-size: 12px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
      }
      h1 {
        margin: 0 0 10px;
        font-size: clamp(2rem, 5vw, 3.4rem);
        line-height: 1.05;
      }
      h2 {
        margin: 0;
      }
      p {
        margin: 0;
        color: var(--muted);
        line-height: 1.6;
      }
      .stack {
        display: grid;
        gap: 10px;
      }
      .grid {
        display: grid;
        gap: 20px;
        margin-top: 24px;
      }
      @media (min-width: 860px) {
        .grid {
          grid-template-columns: 1.2fr 0.8fr;
        }
      }
      .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }
      .pill {
        padding: 10px 14px;
        border: 1px solid var(--border);
        border-radius: 999px;
        background: rgba(31, 138, 91, 0.07);
        font-size: 14px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th,
      td {
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
        text-align: left;
        vertical-align: top;
      }
      th {
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }
      code,
      pre {
        font-family: "SFMono-Regular", "Menlo", monospace;
      }
      pre {
        margin: 0;
        padding: 16px;
        overflow: auto;
        background: #14221a;
        color: #e8f7ee;
        border-radius: 16px;
        font-size: 13px;
      }
      .footer {
        margin-top: 22px;
        font-size: 14px;
        color: var(--muted);
      }
      a {
        color: var(--accent);
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">ConfigHub SDK Demo</p>
        <h1>JavaScript app with live feature flag evaluation.</h1>
        <p>
          This sample app fetches <code>config.json</code> from
          <code>${escapeHtml(baseUrl)}</code>, evaluates flags for a demo user,
          and renders both example values and the full resolved flag map.
        </p>
        <div class="pill-row">
          <div class="pill">identifier: <strong>${escapeHtml(user.identifier)}</strong></div>
          <div class="pill">country: <strong>${escapeHtml(user.country)}</strong></div>
          <div class="pill">plan: <strong>${escapeHtml(user.plan)}</strong></div>
        </div>
      </section>

      <section class="grid">
        <article class="card">
          <div class="stack">
            <h2>Example evaluations</h2>
            <p>
              These use <code>client.getValue(...)</code> with fallback values.
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
              ${exampleRows}
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
              <a href="/api/flags?identifier=${encodeURIComponent(user.identifier)}&country=${encodeURIComponent(user.country)}&plan=${encodeURIComponent(user.plan)}">
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
            This uses <code>client.getAllValues(user)</code>.
          </p>
        </div>
        <pre>${allFlagsJson}</pre>
      </section>

      <p class="footer">
        Tip: create a few flags in ConfigHub, attach them to the SDK key you use here,
        and refresh this page to see the values update.
      </p>
    </main>
  </body>
</html>`;
}

async function handleRequest(req, res) {
  const url = new URL(
    req.url || "/",
    `http://${req.headers.host || "localhost"}`,
  );
  const user = getUser(url.searchParams);
  const baseUrl = (process.env.CONFIGHUB_BASE_URL || DEFAULT_BASE_URL).trim();

  let confighubClient;
  try {
    confighubClient = await getClient();
  } catch (error) {
    return sendJson(res, 500, {
      error: error instanceof Error ? error.message : "Unknown error",
      hint: "Set CONFIGHUB_SDK_KEY before starting the sample app.",
    });
  }

  if (url.pathname === "/health") {
    return sendJson(res, 200, {
      status: "ok",
      sdkConnected: confighubClient.getConfig() !== null,
    });
  }

  if (url.pathname === "/api/flags") {
    const allValues = confighubClient.getAllValues(user);
    const exampleValues = getExampleValues(confighubClient, user);
    return sendJson(res, 200, {
      user,
      exampleValues,
      allValues,
    });
  }

  if (url.pathname !== "/") {
    return sendJson(res, 404, { error: "Not found" });
  }

  const allValues = confighubClient.getAllValues(user);
  const exampleValues = getExampleValues(confighubClient, user);
  const html = renderHomePage(user, allValues, exampleValues, baseUrl);
  return sendHtml(res, 200, html);
}

const port = Number.parseInt(process.env.PORT || String(DEFAULT_PORT), 10);
const server = http.createServer((req, res) => {
  handleRequest(req, res).catch((error) => {
    sendJson(res, 500, {
      error: error instanceof Error ? error.message : "Unknown error",
    });
  });
});

server.listen(port, () => {
  console.log(`ConfigHub JS SDK sample running at http://localhost:${port}`);
});
