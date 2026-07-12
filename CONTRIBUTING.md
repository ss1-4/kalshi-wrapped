# Contributing

There's no build step. Edit `index.html`, refresh your browser, done. Everything — markup, styles, and logic — lives in that one file, deliberately.

## The most useful thing you can do right now

Report CSV column-mapping mismatches. Kalshi's export headers have varied across versions, and the app's lenient `detectColumns()` step only knows the keywords it's been taught.

If your export doesn't parse:

1. Open an issue.
2. Paste **just the header row** of your CSV (redact anything sensitive — we only need column names, never trade data).
3. Say which stat came out wrong or missing.

Fixes are usually a one-line addition to the `COLUMN_KEYWORDS` object in `index.html` — pull requests for those are very welcome.
