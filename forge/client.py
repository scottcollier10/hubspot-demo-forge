"""HubSpot API client — zero-dependency urllib.request wrapper."""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "https://api.hubapi.com"
RATE_LIMIT_DELAY = 0.15  # seconds between writes — stays under 10 req/sec
BATCH_LIMIT = 100


class HubSpotClient:
    def __init__(self, token: str):
        self.token = token

    @classmethod
    def from_env(cls) -> "HubSpotClient":
        token = os.environ.get("HUBSPOT_TOKEN", "")
        if not token:
            print("ERROR: HUBSPOT_TOKEN not set.")
            print("  Run: export HUBSPOT_TOKEN=pat-na1-xxxxx")
            sys.exit(1)
        return cls(token)

    def _request(self, method: str, path: str, body: dict | None = None):
        url = f"{BASE_URL}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as response:
                raw = response.read().decode()
                return (json.loads(raw) if raw else {}), response.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return (json.loads(raw) if raw else {}), e.code

    def post(self, path: str, body: dict) -> tuple[dict, int]:
        return self._request("POST", path, body)

    def get(self, path: str) -> dict:
        data, _ = self._request("GET", path)
        return data

    def patch(self, path: str, body: dict) -> dict | None:
        data, status = self._request("PATCH", path, body)
        if status >= 400:
            print(f"    WARNING: PATCH failed {status}: {json.dumps(data)[:120]}")
            return None
        return data

    def put(self, path: str) -> tuple[dict, int]:
        return self._request("PUT", path)

    def fetch_all(self, path: str, body: dict) -> list[dict]:
        """Paginate through a search endpoint. Returns all results."""
        results = []
        after = None

        while True:
            page_body = {**body, "limit": BATCH_LIMIT}
            if after:
                page_body["after"] = after

            data, status = self.post(path, page_body)
            if status != 200:
                print(f"  ERROR fetching {path}: {status}")
                break

            results.extend(data.get("results", []))

            paging = data.get("paging", {})
            after = paging.get("next", {}).get("after")
            if not after:
                break

        return results

    def batch_update(self, object_type: str, inputs: list[dict]) -> bool:
        """Batch update objects in chunks of BATCH_LIMIT."""
        for i in range(0, len(inputs), BATCH_LIMIT):
            chunk = inputs[i : i + BATCH_LIMIT]
            _, status = self.post(
                f"/crm/v3/objects/{object_type}/batch/update",
                {"inputs": chunk},
            )
            if status != 200:
                print(f"  ERROR batch update: {status}")
                print(f"  Response: {json.dumps(_)[:500]}")
                return False
        return True

    def batch_archive(self, object_type: str, ids: list[str]) -> bool:
        """Batch archive (soft-delete) objects in chunks of BATCH_LIMIT."""
        for i in range(0, len(ids), BATCH_LIMIT):
            chunk = ids[i : i + BATCH_LIMIT]
            _, status = self.post(
                f"/crm/v3/objects/{object_type}/batch/archive",
                {"inputs": [{"id": oid} for oid in chunk]},
            )
            if status not in (200, 204):
                print(f"  ERROR batch archive {object_type}: {status}")
                return False
            self.throttle()
        return True

    def throttle(self):
        """Rate limit delay between API calls."""
        time.sleep(RATE_LIMIT_DELAY)
