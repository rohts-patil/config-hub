from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SDK_ROOT = ROOT / "packages" / "sdk-python"
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from confighub_sdk import ConfigHubClient  # noqa: E402


def test_client_force_refresh_uses_etag_and_preserves_config_on_304():
    responses = [
        (
            200,
            {"ETag": "v1"},
            b'{"settings":{"new_dashboard":{"value":true}},"segments":[]}',
        ),
        (304, {}, b""),
    ]
    recorded_headers: list[dict[str, str]] = []

    def request_fn(_url: str, headers: dict[str, str]):
        recorded_headers.append(dict(headers))
        return responses.pop(0)

    client = ConfigHubClient(
        "sdk-key",
        base_url="http://localhost:8000",
        poll_interval_seconds=0,
        request_fn=request_fn,
    )

    client.force_refresh()
    first_config = client.get_config()
    client.force_refresh()

    assert first_config is not None
    assert first_config == client.get_config()
    assert recorded_headers[0] == {}
    assert recorded_headers[1]["If-None-Match"] == "v1"


def test_client_evaluates_targeted_values_and_reports_callbacks():
    evaluated: list[tuple[str, object, dict[str, object] | None]] = []

    def request_fn(_url: str, _headers: dict[str, str]):
        return (
            200,
            {},
            b"""
            {
              "settings": {
                "welcome_message": {
                  "value": "Hello",
                  "targetingRules": [
                    {
                      "conditions": [
                        {
                          "attribute": "plan",
                          "comparator": "equals",
                          "comparisonValue": "pro"
                        }
                      ],
                      "value": "Welcome, pro user"
                    }
                  ]
                }
              },
              "segments": []
            }
            """,
        )

    client = ConfigHubClient(
        "sdk-key",
        base_url="http://localhost:8000",
        poll_interval_seconds=0,
        request_fn=request_fn,
        on_flag_evaluated=lambda key, value, user: evaluated.append((key, value, user)),
    )

    client.force_refresh()
    value = client.get_value(
        "welcome_message",
        "Fallback",
        {"identifier": "user-1", "plan": "pro"},
    )
    all_values = client.get_all_values({"identifier": "user-2", "plan": "free"})

    assert value == "Welcome, pro user"
    assert all_values == {"welcome_message": "Hello"}
    assert evaluated[0][0] == "welcome_message"
    assert evaluated[0][1] == "Welcome, pro user"
    assert evaluated[1][0] == "welcome_message"
    assert evaluated[1][1] == "Hello"
