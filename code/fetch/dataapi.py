#!/usr/bin/env python3
"""dataapi.py: the named wallet's activity rows from Polymarket's public Data API.

Reads GET /v2/activity (no key, read-only) with cursor pagination and writes the rows to
out/dataapi_activity.json in the field names of the original v1 route, which is the shape
recompute.py reads. The shipped code/raw/dataapi_activity.json was captured from the v1
route before Polymarket retired it on 2 November 2026. On 2026-11-08 v2 returned the same
17 rows.

Usage:
  python3 -I code/fetch/dataapi.py        (writes code/fetch/out/dataapi_activity.json)
Set FETCH_OUT to write elsewhere. Standard library only.
"""
import json
import os
import urllib.parse
import urllib.request
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("FETCH_OUT") or os.path.join(BASE, "out")
URL = "https://data-api.polymarket.com/v2/activity"
W = "0x31a56e9e690c621ed21de08cb559e9524cdb8ed9"
HDRS = {"User-Agent": "polymarket-vandyke-receipts/1.0", "Accept": "application/json"}

# v2 field -> v1 field, for the fields that changed name
V1_NAMES = {"proxy_wallet": "proxyWallet", "condition_id": "conditionId", "usdc_size": "usdcSize",
            "transaction_hash": "transactionHash", "token_id": "asset", "outcome_index": "outcomeIndex",
            "event_slug": "eventSlug", "profile_image": "profileImage",
            "profile_image_optimized": "profileImageOptimized"}


def get(params):
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params), headers=HDRS)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, cursor = [], None
    while True:
        params = {"user": W, "limit": 500}
        if cursor:
            params["cursor"] = cursor
        page = get(params)
        rows.extend(page.get("data") or [])
        cursor = (page.get("pagination") or {}).get("next_cursor")
        if not cursor:
            break
    rows = [{V1_NAMES.get(k, k): v for k, v in r.items()} for r in rows]
    print("activity rows:", len(rows), dict(Counter(r.get("type") for r in rows)))
    path = os.path.join(OUT, "dataapi_activity.json")
    with open(path, "w") as f:
        json.dump(rows, f)
    print("wrote", path)


if __name__ == "__main__":
    main()
