# Match Report

Turn your Kalshi trade history into a shareable, stadium-ticket-styled stat card — entirely in your browser.

**Live:** _[GitHub Pages link goes here once deployed]_

## Why this exists

Every existing tool in the Kalshi ecosystem — TradesViz, Kalshi Dash, Kalshi Analytics — is built for people who already think in Sharpe ratios and drawdowns. Match Report is for everyone else: the person who put $20 on the World Cup because of a Timothée Chalamet ad and wants something worth screenshotting, not a risk dashboard. It takes your exported trade history and produces one portrait card — win–loss record, streak, biggest call, and a calibration score that shows how close your stated confidence was to what actually happened. Think Spotify Wrapped for your predictions.

Nothing leaves your browser. There's no backend, no account, no analytics — the CSV is parsed in client-side JavaScript and the card is rendered as DOM, exported to PNG locally.

## Run it locally

It's a single static HTML file. No build step, no server:

```
open index.html
```

(or just double-click it.)

## Deploy to GitHub Pages

1. Push this repo to GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select `main` and `/ (root)`, and save.
4. Your app will be live at `https://<username>.github.io/match-report/` within a minute or two.

## World Cup Wrapped

If the data contains World Cup trades (tickers matching `WC`, or a soccer/World Cup category), a **View your World Cup Wrapped** button appears under the main card. It opens a stepped, Spotify-Wrapped-style sequence built from just the tournament subset: your record, the picks you kept coming back to (with P&L per pick), your best call and longest shot landed, your betting habits (per-pick records, busiest matchday, best day, how often you backed the draw or bet against), and your sharpness score. Every slide downloads as its own PNG. Nothing about the input changes — same CSV or API JSON, the tournament cut is automatic.

## Test data & stress testing

`scripts/generate_test_data.py` produces realistic simulated trade histories — World-Cup-heavy, with outcomes statistically consistent with entry prices so the calibration score behaves like a real trader's. It emits four formats (two CSV header schemas, a deliberately messy CSV with CRLF/quoted-comma/currency-formatted values, and the API JSON shape); ready-made samples live in `testdata/`. Drag any of them into the app to demo it without real data.

```
python scripts/generate_test_data.py --n 40 --format json --seed 7 > sample.json
python scripts/generate_test_data.py --all --outdir testdata
```

## Automatic import (Kalshi API)

Beyond CSV, the app accepts the raw JSON from Kalshi's `GET /trade-api/v2/portfolio/settlements` endpoint — paste the response body (a single page, an array, or several concatenated pages) or drop it as a `.json` file. Settlement records carry everything the card needs: P&L is computed as revenue minus contract cost minus fees, and your average cost per contract becomes the stated confidence for the calibration score.

`scripts/fetch_settlements.py` automates the pull: it signs requests with your API key (RSA-PSS, per [Kalshi's auth docs](https://docs.kalshi.com/getting_started/api_keys)), paginates both the live and historical tiers, and writes a `settlements.json` you can drop straight into the app.

```
pip install requests cryptography
python scripts/fetch_settlements.py --key-id YOUR_KEY_ID --key-file kalshi-key.pem
```

**Why isn't there a "Connect Kalshi" button?** Two reasons. Kalshi's API is built for server-side use and doesn't permit direct calls from third-party websites (its signed-header auth triggers CORS checks the API doesn't answer). And the credential involved is an RSA private key that can also sign *trading* requests — asking people to paste that into a webpage would be a bad habit to teach, even though this app never sends anything anywhere. The script keeps the key on your machine, where it belongs. If Kalshi ever ships browser-friendly, read-only credentials, a one-click connect flow becomes a small change.

## How column detection works (and how to fix it)

Kalshi's export column names have varied across versions, so the app doesn't assume a rigid schema. Instead, `detectColumns()` in `index.html` scans the header row for case-insensitive keyword matches:

| Field    | Matched if the header contains…     |
|----------|-------------------------------------|
| ticker   | `ticker`, `market`, `event`         |
| pnl      | `pnl`, `profit`, `realized`         |
| result   | `result`, `status`, `outcome`       |
| price    | `price`, `yes_price`, `avg_price`   |
| date     | `date`, `time`, `created`           |
| category | `category`, `series`                |

If a real export doesn't parse cleanly, the fix is almost always adding a keyword to the `COLUMN_KEYWORDS` object near the top of the `<script>` block in `index.html`. Win/loss classification prefers a numeric P&L column (positive = win); if there isn't one, it falls back to win/loss keywords in the result column; rows that can't be classified either way are skipped rather than guessed at.

## Status

Shipped fast on purpose — this is a seed test to see whether casual traders actually want a shareable card. Expect rough edges; report them.

---

*Unofficial. Not affiliated with Kalshi.*
