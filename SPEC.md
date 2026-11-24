# Alevi Calendar: API & Embeddable Widget (Spec)

Status: **idea / not started** · Written: 2026-11-18

## Goal

Take the Alevi calendar from http://www.alevitischer-kalender.de/, turn it into clean data, and offer it as:

1. a **JSON API** other sites can use,
2. an **embeddable widget** (a clickable list of events) that works on WordPress and other website builders,
3. **calendar integration**, so people can add the events to their own calendar app, either as a live subscription or as a one-time download.

## Source data (checked 2026-11-18)

- WordPress 5.9 site. The events are **plain text on the homepage**. There is no feed, iCal file or API for them.
- About 13 events per year, currently for **2026, 2027 and 2028**. The site is updated about once a year (the PDF version was uploaded in Dec 2025).
- HTTPS on the site is broken (TLS handshake failure), so fetch it over **http**.
- The date formats are inconsistent, so the parser must handle all of these:
  - single day: `10. MÄRZ 2026`
  - range: `10. – 12. FEBRUAR 2026`
  - two days: `05./06. MAI 2026`
  - extra whitespace: `09. – 11. FEBRUAR  2027`
  - a note on the same line as the date: `21. MÄRZ 2028 (21. März 598)`
- Some entries have a second line with a note, e.g. `(21. RAMAZAN 40 HIDSCHRA-MONDKALENDER)`.
- **Probable typo in the source:** Fatma-Ana-Fasten 2027 shows `05. JULI 2027`, but it sits between 04 and 06 June, so it is most likely 05. JUNI. Confirm with the site owner and keep a manual override for it.
- The page carries a "© Alevitischer Kalender" notice. **Ask the owner for permission before going public.** They might also provide the data directly.

## Architecture

The data changes once a year, so build it as **static files**. No server that scrapes live on every request.

```
scraper (run yearly or on a schedule)
   └─► events.json        ← the "API"
   └─► alevi.ics          ← calendar subscription / download
   └─► events/<id>.ics    ← single-event downloads
widget: alevi-calendar.js  (reads events.json + links.json)
links.json                 (event key → URL, maintained by hand)
```

- **Hosting:** a free static host (GitHub Pages, Netlify or Cloudflare Pages) under our own domain, e.g. `kalender.example.de`.
- **Scraper:** a scheduled job (e.g. GitHub Actions, weekly) re-scrapes the site and commits the output only when the data changed. If parsing fails or returns far fewer events than before, it keeps the last good data and reports an error.
- **Overrides:** `overrides.json` for manual fixes (typos, missing years), applied after scraping.

## Data model (`events.json`)

```json
{
  "source": "http://www.alevitischer-kalender.de/",
  "updated": "2026-11-18T10:00:00Z",
  "events": [
    {
      "id": "2026-hizir-fasten",
      "key": "hizir-fasten",
      "title": "Hızır-Fasten",
      "start": "2026-02-10",
      "end": "2026-02-12",
      "note": null,
      "category": "fasten",
      "url": "https://…"
    }
  ]
}
```

- `key` is the same every year (e.g. `sivas`, `asure`, `nevruz`). Links and colours are attached by `key`.
- `end` is inclusive in the JSON. It is only converted to an exclusive end date in the iCal output.
- `category`: `fasten` | `gedenktag` | `fest`.
- `url` comes from `links.json`. If an event has no link, `url` is `null` and the event is not clickable.

## Feature: calendar integration

### A) Subscribe (live, stays up to date)

Users add our feed URL once, and their calendar app pulls updates automatically. When a new year is published, it appears in their calendar without them doing anything.

- Feed: `https://<domain>/alevi.ics`. It is also offered as `webcal://<domain>/alevi.ics`, which opens the calendar app directly on most devices.
- The widget gets an **"Abonnieren"** button with a small menu:
  - **Apple / iOS / macOS:** `webcal://<domain>/alevi.ics`
  - **Google Calendar:** `https://calendar.google.com/calendar/r?cid=webcal://<domain>/alevi.ics`
  - **Outlook.com / Microsoft 365:** `https://outlook.live.com/calendar/0/addfromweb?url=https://<domain>/alevi.ics&name=Alevitischer%20Kalender`
  - **Copy link:** copies the https URL so users can paste it into any other app.
- Note: Google refreshes subscribed calendars slowly (often 12–24 h or more). That is fine for yearly data.

### B) Download (one-time import)

The events are imported as a snapshot. Later changes do **not** sync.

- **Whole calendar:** a "Download (.ics)" link to `alevi.ics`, served with `Content-Disposition: attachment` where the host allows it. Otherwise use the HTML `download` attribute.
- **Single event:** each event in the widget gets an "add to calendar" icon that downloads `events/<id>.ics`. Optionally also offer a Google "Add event" link: `https://calendar.google.com/calendar/render?action=TEMPLATE&text=…&dates=20260210/20260213&details=…`

### iCal requirements

- `Content-Type: text/calendar; charset=utf-8`. Check that the chosen host actually sends this.
- All-day events: `DTSTART;VALUE=DATE:20260210` and `DTEND;VALUE=DATE:20260213` (**the end date is exclusive**, so add one day).
- **Stable `UID` per event** (e.g. `2026-hizir-fasten@<domain>`), so re-imports and feed updates don't create duplicates.
- Set `X-WR-CALNAME:Alevitischer Kalender` and `X-WR-TIMEZONE:Europe/Berlin`.
- Set `REFRESH-INTERVAL;VALUE=DURATION:P1D` and `X-PUBLISHED-TTL:P1D`.
- Put the note in `DESCRIPTION` and the event link in `URL`.
- Validate the output with an iCal validator, then test it in Apple Calendar, Google Calendar and Outlook.

## Feature: widget

- Embed with a script tag (works in a WordPress "Custom HTML" block):
  ```html
  <script src="https://<domain>/alevi-calendar.js" defer></script>
  <alevi-calendar lang="de"></alevi-calendar>
  ```
- **iframe fallback** for builders that block scripts (Wix, Squarespace, Jimdo, …):
  `<iframe src="https://<domain>/embed.html?lang=de" …></iframe>`
- Built as a web component with **Shadow DOM**, so the host site's theme CSS can't break it.
- **Design:** accent colour **#cc2d1d** (date badge, hover, buttons), text colour **#68686b**. Clean list, month/day badge per event, the next upcoming event highlighted.
- Clickable events open `url` (from `links.json`), in a new tab if configured.
- Responsive layout. Readable on mobile at 320 px width.
- Attributes: `lang` (de/tr?), `year`, `target`. (`mode`/`limit` removed 2026-11-19.)
- Footer: the "Abonnieren" and "Download" buttons (see above) and a source credit linking to alevitischer-kalender.de.

## Open questions

- [x] Permission from the site owner: granted.
- [x] Languages: de / tr / en.
- [x] Single view: full year, opens at the year of the next event, prev/next year buttons. No "upcoming" view and no per-event download (removed 2026-11-19 at user's request).
- [x] Event links: `links.json` filled (bdaj.de/Kalender anchors).
- [x] Fatma-Ana-Fasten 2027: source now correct (5 June 2027).
- [ ] Missing in the source for 2026+: Hz. Ali Todestag, Gadir Hum, Hz. Hüseyin. Insert them with `scripts/override.py add`.
- [ ] Deployment to cemcolak.de/alevi-kalender/ (needs server access; set `deploy_target` in config.json).
- [ ] Test the iCal feeds in Apple / Google / Outlook (owner).

## Manual data (overrides)

`data/overrides.json` is the only place for manual data. It is read on every build and never written by the scraper:

- `add`: events the source does not have. If the source later has the same id, the manual entry wins and the build log says so.
- `fix`: change dates of a scraped event.
- `remove`: hide a scraped event.

`data/last-good.json` holds only the *scraped* events. When the source is down, the build falls back to it and still applies the overrides.
Use `scripts/override.py` (list / add / fix / remove / drop / keys) instead of editing the JSON by hand.

## Scheduled rebuild

`scripts/update.sh` runs daily at 04:17 via root's crontab: build, then `rsync --delete dist/ <deploy_target>` if set. Log: `logs/update.log`.

## Effort estimate

| Part | Effort |
|---|---|
| Scraper + parser (messy dates, overrides) | 2–4 h |
| JSON + iCal feed + single-event .ics files | 2–3 h |
| Widget (UI, mobile, script + iframe embed, subscribe/download menu) | 4–6 h |
| Hosting, scheduled job, docs | 1–2 h |
| **Total** | **≈ 1.5–2 days** |
