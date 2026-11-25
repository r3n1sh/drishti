# Drishti India Desk

A map-first situation desk for India. Every state and district on one interactive map, with live layers and signals that follow you as you drill down.

## What's live

| Layer / section | Source | Refresh |
|---|---|---|
| Air quality (Indian NAQI) | CAMS model via Open-Meteo, PM2.5/PM10 → CPCB breakpoints | hourly, 72 h history |
| Heat, cold, rain | Open-Meteo | hourly |
| Fire hotspots | NASA FIRMS VIIRS (NOAA-20/21, Suomi NPP) | hourly |
| Earthquakes | USGS FDSN, M ≥ 2.5 | hourly |
| Cyclones | GDACS | hourly |
| Official alerts (with areas) | NDMA SACHET CAP (IMD, SDMAs, CWC, INCOIS) | hourly |
| Official releases | RBI, PIB RSS | hourly |
| Press signals | Google News RSS + GDELT | hourly |
| World → India | Google News (international stories mentioning India) | hourly |
| Social pulse | Bluesky news accounts, Mastodon hashtags | hourly |
| Government schemes | Curated list (`schemes.json`) + live scheme news | list: manual; news: hourly |

Power grid, markets, rail/air, digital and agriculture panels still show **sample** data.

## How it works

- `index.html` is the whole app (D3 + TopoJSON from CDNs, no build step).
- `scripts/fetch_feeds.py` (standard library only) pulls every source and writes one JSON file per feed.
- `.github/workflows/refresh-feeds.yml` runs the fetcher every hour and force-pushes the results to the single-commit `feeds` branch, so `main` never accumulates data history.
- The page reads `https://raw.githubusercontent.com/<owner>/<repo>/feeds/data/*.json` (needs a **public** repo) and falls back to the snapshot in `/data`.
- Vercel deploys `main` as a static site.

## Run locally

```bash
python3 -I scripts/fetch_feeds.py india.json data   # refresh the snapshot
python3 -m http.server 8000                          # open http://localhost:8000
```

## Notes

- Boundaries: [india-maps-data](https://github.com/udit-001/india-maps-data) (2019 states and districts), simplified. Neighbours: Natural Earth via world-atlas.
- District values are modelled from state readings until district-level feeds are added.
- Check source terms before commercial use: Open-Meteo requires a paid plan for commercial use; Google News and social posts are shown as headlines with links only.
- X (Twitter) is not integrated; it needs a paid API key.
