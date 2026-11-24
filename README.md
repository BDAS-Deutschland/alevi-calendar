# Alevi Calendar

The Alevi holiday calendar as a subscribable iCal feed, a JSON file and an embeddable widget (DE / TR / EN).
Live at **https://kalender.bdas.de/**.

The dates are scraped from the source site once a day and published as static files. No server-side code runs on requests.
Design and background: [SPEC.md](SPEC.md).

## Layout

| Path | What |
|---|---|
| `scripts/build.py` | Scrapes the source, applies manual overrides, writes everything to `dist/` (Python 3, standard library only) |
| `scripts/update.sh` | Daily job: build, then rsync `dist/` to `deploy_target` |
| `scripts/override.py` | Edits manual corrections in `data/overrides.json` |
| `widget/` | Widget (`alevi-calendar.js`), landing page, embed page |
| `data/` | `overrides.json` (manual corrections), `catalog.json`, `links.json`, `last-good.json` (fallback if scraping fails) |
| `config.json` | Base URL, UID domain, calendar names, deploy target |
| `deploy/` | Caddy config and crontab used on the server |

`dist/` and `logs/` are generated and not in git.

## Usage

```sh
python3 scripts/build.py           # build into dist/
scripts/update.sh                  # build + publish (what cron runs)
python3 scripts/override.py --help # fix / add / remove events by hand
```

## Published URLs

| URL | What |
|---|---|
| `/abo-de`, `/abo-tr`, `/abo-en` (`/abo` = German) | iCal subscription feeds |
| `/download-de`, … | Same feeds, as a file download |
| `/widget.js` | The widget: `<script src="https://kalender.bdas.de/widget.js"></script><alevi-calendar></alevi-calendar>` |
| `/embed` | Widget as an iframe page |
| `/events.json` | All events as JSON |

## Server setup

1. Install `python3`, `rsync` and Caddy.
2. Clone this repo to `/root/alevi-calendar` and run `scripts/update.sh` once.
3. Add the blocks from `deploy/Caddyfile` to the Caddy config (adjust `root` to `/srv/alevi-kalender` when Caddy runs outside Docker).
4. Install the cron line from `deploy/crontab`.
5. Point DNS for `kalender.bdas.de` to the server.

Keep the domain and `uid_domain` unchanged: every subscription points to them, so changing either breaks updates for existing subscribers or creates duplicate events.
