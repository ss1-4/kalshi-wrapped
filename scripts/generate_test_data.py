#!/usr/bin/env python3
"""Generate realistic simulated Kalshi trade data for stress-testing Match Report.

Produces trade histories skewed toward 2026 World Cup markets, with outcomes
statistically consistent with entry prices (so the calibration score behaves
like a real trader's would), in several formats:

  csv-v1   header style: ticker, side, avg_price (cents), count, realized_pnl, status, created_time
  csv-v2   header style: Market, Series, Result, Profit/Loss, Yes Price (0-1), Settled Date
  messy    csv-v1 but with CRLF line endings, quoted fields with commas,
           currency symbols, parenthesized negatives, stray blank lines,
           and a few unclassifiable rows
  json     GET /portfolio/settlements response shape

Usage:
    python generate_test_data.py --n 40 --format csv-v1 --seed 7 > sample.csv
    python generate_test_data.py --n 500 --format json --seed 7 > sample.json
    python generate_test_data.py --all --outdir ../testdata   # one file per format

The simulated trader has a slight edge (--edge, default 0.03): their picks win
about 3 points more often than the price implies. Set --edge 0 for a perfectly
calibrated trader or negative for a losing one.
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

WC_TEAMS = ["BRA", "ARG", "FRA", "ENG", "ESP", "GER", "POR", "NED", "USA",
            "MEX", "MAR", "JPN", "KOR", "URU", "COL", "CRO", "SEN", "GHA"]
OTHER_SERIES = [
    ("KXNBAFINALS", ["OKC", "NYK"]),
    ("KXWTAMATCH", ["SWIATEK", "GAUFF", "SABALENKA"]),
    ("KXUFC", ["PEREIRA", "JONES"]),
]

WC_START = datetime(2026, 6, 11)
WC_END = datetime(2026, 7, 19)


def make_trade(rng, edge, wc_share):
    """One settled trade: returns a dict of canonical fields."""
    when = WC_START + timedelta(
        seconds=rng.randint(0, int((WC_END - WC_START).total_seconds())))
    if rng.random() < wc_share:
        team = rng.choice(WC_TEAMS)
        opp = rng.choice([t for t in WC_TEAMS if t != team])
        pick = "TIE" if rng.random() < 0.12 else team  # some bets back the draw
        ticker = f"KXWCGAME-26{when.strftime('%b%d').upper()}{team}{opp}-{pick}"
        series = "KXWCGAME"
        title = f"Will {team} beat {opp}?" if pick != "TIE" else f"Will {team} vs {opp} end in a draw?"
    else:
        series, sides = rng.choice(OTHER_SERIES)
        side = rng.choice(sides)
        ticker = f"{series}-26-{side}"
        title = f"{series} market, {side}"

    # Entry price as implied probability; outcome consistent with price + edge
    price = round(rng.uniform(0.08, 0.92), 2)
    won = rng.random() < min(0.98, max(0.02, price + edge))
    count = rng.choice([5, 10, 10, 15, 20, 25, 50])
    cost = round(price * count, 2)
    fee = round(0.07 * price * (1 - price) * count, 2)
    revenue_cents = count * 100 if won else 0
    pnl = round(revenue_cents / 100 - cost - fee, 2)

    return {
        "ticker": ticker, "series": series, "title": title, "won": won,
        "price": price, "count": count, "cost": cost, "fee": fee,
        "revenue_cents": revenue_cents, "pnl": pnl, "when": when,
    }


def to_csv_v1(trades):
    lines = ["ticker,side,avg_price,count,realized_pnl,status,created_time"]
    for t in trades:
        lines.append(f"{t['ticker']},yes,{int(t['price']*100)},{t['count']},"
                     f"{t['pnl']},settled,{t['when'].isoformat()}Z")
    return "\n".join(lines) + "\n"


def to_csv_v2(trades):
    lines = ["Market,Series,Result,Profit/Loss,Yes Price,Settled Date"]
    for t in trades:
        result = "Won" if t["won"] else "Lost"
        lines.append(f"{t['ticker']},{t['series']},{result},{t['pnl']},"
                     f"{t['price']},{t['when'].strftime('%m/%d/%Y')}")
    return "\n".join(lines) + "\n"


def to_messy(trades, rng):
    lines = ["ticker,market_title,avg_price,realized_pnl,status,created_time"]
    for i, t in enumerate(trades):
        pnl = f"(${abs(t['pnl']):,.2f})" if t["pnl"] < 0 else f"${t['pnl']:,.2f}"
        title = f'"{t["title"]}, group stage"'  # quoted field containing a comma
        lines.append(f"{t['ticker']},{title},{int(t['price']*100)},"
                     f'"{pnl}",settled,{t["when"].isoformat()}Z')
        if i % 9 == 4:
            lines.append("")  # stray blank line
    # a few rows that can't be classified — the app must skip, not choke
    lines.append("KXWCGAME-26-PENDING,\"Still open, no result\",55,,open,")
    lines.append(",,,,,")
    return "\r\n".join(lines) + "\r\n"


def to_json(trades):
    settlements = []
    for t in trades:
        settlements.append({
            "ticker": t["ticker"],
            "event_ticker": t["ticker"].rsplit("-", 1)[0],
            "market_result": "yes" if t["won"] else "no",
            "yes_count_fp": f"{t['count']:.2f}",
            "yes_total_cost_dollars": f"{t['cost']:.4f}",
            "no_count_fp": "0.00",
            "no_total_cost_dollars": "0.0000",
            "revenue": t["revenue_cents"],
            "fee_cost": f"{t['fee']:.4f}",
            "settled_time": t["when"].isoformat() + "Z",
        })
    return json.dumps({"settlements": settlements, "cursor": ""}, indent=1)


FORMATS = {"csv-v1": to_csv_v1, "csv-v2": to_csv_v2, "messy": None, "json": to_json}
EXT = {"csv-v1": "csv", "csv-v2": "csv", "messy": "csv", "json": "json"}


def render(fmt, trades, rng):
    return to_messy(trades, rng) if fmt == "messy" else FORMATS[fmt](trades)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=40, help="number of settled trades (default 40)")
    ap.add_argument("--format", choices=list(FORMATS), default="csv-v1")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--edge", type=float, default=0.03,
                    help="trader edge over the price, in probability points (default 0.03)")
    ap.add_argument("--wc-share", type=float, default=0.8,
                    help="fraction of trades that are World Cup markets (default 0.8)")
    ap.add_argument("--all", action="store_true", help="write one file per format")
    ap.add_argument("--outdir", default=".", help="output directory for --all")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    trades = sorted((make_trade(rng, args.edge, args.wc_share) for _ in range(args.n)),
                    key=lambda t: t["when"])

    if args.all:
        os.makedirs(args.outdir, exist_ok=True)
        for fmt in FORMATS:
            path = os.path.join(args.outdir, f"sample-{fmt}.{EXT[fmt]}")
            with open(path, "w", newline="") as f:
                f.write(render(fmt, trades, rng))
            print(f"wrote {path}", file=sys.stderr)
    else:
        sys.stdout.write(render(args.format, trades, rng))


if __name__ == "__main__":
    main()
