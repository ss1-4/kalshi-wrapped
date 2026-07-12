#!/usr/bin/env python3
"""Fetch your Kalshi settlement history as JSON that Match Report accepts.

The web app can't call Kalshi's API directly from the browser (the API is
built for server-side use), so this script is the automation seam: run it,
then drop or paste the resulting JSON into the app.

Usage:
    pip install requests cryptography
    python fetch_settlements.py --key-id YOUR_KEY_ID --key-file kalshi-key.pem
    # writes settlements.json in the current directory

Get a key ID + private key from kalshi.com -> Account Settings -> API Keys.
The private key is shown once and never stored by Kalshi — keep the .pem safe.
Note: this key can also sign trading requests; this script only ever reads.

Auth per https://docs.kalshi.com/getting_started/api_keys :
sign `timestamp_ms + METHOD + path` (path without query string) with
RSA-PSS / SHA-256 / MGF1-SHA256 / salt = digest length, base64-encoded.
"""

import argparse
import base64
import json
import sys
import time

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

BASE = "https://api.elections.kalshi.com"
LIVE_PATH = "/trade-api/v2/portfolio/settlements"
HIST_PATH = "/trade-api/v2/historical/settlements"


def load_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def signed_headers(key, key_id, method, path):
    ts = str(int(time.time() * 1000))
    msg = (ts + method + path.split("?")[0]).encode("utf-8")
    sig = key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode("utf-8"),
    }


def fetch_all(key, key_id, path):
    """Paginate one settlements endpoint; returns a list (empty on 404)."""
    out, cursor = [], None
    while True:
        query = "?limit=200" + (f"&cursor={cursor}" if cursor else "")
        resp = requests.get(
            BASE + path + query,
            headers=signed_headers(key, key_id, "GET", path),
            timeout=30,
        )
        if resp.status_code == 404:
            return out  # endpoint not present for this account/tier
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", "2"))
            print(f"  rate limited, waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        body = resp.json()
        page = body.get("settlements", [])
        out.extend(page)
        cursor = body.get("cursor")
        if not cursor or not page:
            return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--key-id", required=True, help="Kalshi API key ID")
    ap.add_argument("--key-file", required=True, help="Path to the RSA private key (.pem)")
    ap.add_argument("--out", default="settlements.json", help="Output file (default: settlements.json)")
    args = ap.parse_args()

    key = load_key(args.key_file)

    print("Fetching live-tier settlements...", file=sys.stderr)
    settlements = fetch_all(key, args.key_id, LIVE_PATH)

    # Since Feb 2026 Kalshi splits data into live + historical tiers;
    # older records live under /historical/*. Harmless no-op if absent.
    print("Fetching historical-tier settlements...", file=sys.stderr)
    settlements += fetch_all(key, args.key_id, HIST_PATH)

    with open(args.out, "w") as f:
        json.dump({"settlements": settlements}, f, indent=1)

    print(f"Wrote {len(settlements)} settlements to {args.out}", file=sys.stderr)
    print("Drop that file onto Match Report (or paste its contents) to generate your card.", file=sys.stderr)


if __name__ == "__main__":
    main()
