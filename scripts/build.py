#!/usr/bin/env python3
"""Scrape the Alevi holiday list (source_url in config.json) and build the static API, iCal feeds and widget into dist/.

Usage:
    python3 scripts/build.py                 # fetch the live site
    python3 scripts/build.py --html page.html  # parse a saved copy instead
    python3 scripts/build.py --strict        # fail instead of falling back to the last good data

Only the Python standard library is used.
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WIDGET = ROOT / "widget"
DIST = ROOT / "dist"
SNAPSHOT = DATA / "last-good.json"
LANGS = ("de", "tr", "en")

MONTHS = {
    "JANUAR": 1, "FEBRUAR": 2, "MÄRZ": 3, "MAERZ": 3, "MARZ": 3, "APRIL": 4, "MAI": 5,
    "JUNI": 6, "JULI": 7, "AUGUST": 8, "SEPTEMBER": 9, "OKTOBER": 10, "NOVEMBER": 11, "DEZEMBER": 12,
}

# "10. MÄRZ 2026", "10 – 12. FEBRUAR 2026", "05./06. MAI 2026", "27. Mai 2026",
# "25. Mai – 05. Juni 2028" (explicit month change), "29. – 01. Mai 2030" (implicit: 29 April - 1 May),
# "21. MÄRZ 2028 (21. März 598)"
DATE_RE = re.compile(
    r"^(\d{1,2})\.?\s*(?:([A-Za-zÄÖÜäöü]+)\s*(?=[–—-]))?(?:(?:[–—-]|/)\s*(\d{1,2})\.?\s*)?"
    r"([A-Za-zÄÖÜäöü]+)\s+(\d{4})\b(.*)$"
)
YEAR_RE = re.compile(r"^(?:Alevitische Feier- und Gedenktage\s+)?(20\d\d)$", re.I)
END_MARKERS = ("designed by", "©", "yorum gönder", "leave a reply")

# Order matters: first rule whose keywords all appear wins.
RULES = [
    ("hidirellez", ["HIDIRELLEZ"]),
    ("hizir-fasten", ["HIZIR"]),
    ("hz-huseyin", ["HUSEYIN"]),
    ("hz-ali-todestag", ["TODESTAG", "ALI"]),
    ("nevruz", ["NEVRUZ"]),
    ("opferfest", ["OPFERFEST"]),
    ("gadir-hum", ["GADIR"]),
    ("masum-u-paklar", ["MASUM"]),
    ("fatma-ana", ["FATMA"]),
    ("asure", ["ASUR"]),
    ("muharrem", ["MUHARREM"]),
    ("sivas", ["SIVAS"]),
    ("haci-bektas", ["BEKTAS"]),
]

BLOCK_TAGS = r"p|div|br|h[1-6]|li|ul|ol|tr|td|th|table|section|article|header|footer|blockquote|figure"


class ScrapeError(Exception):
    pass


def log(msg):
    print(msg, file=sys.stderr)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


# --------------------------------------------------------------------------- scraping

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; alevi-calendar-sync/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")


def page_lines(raw_html):
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw_html)
    t = re.sub(rf"(?i)</?(?:{BLOCK_TAGS})\b[^>]*>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in t.splitlines() if line.strip()]


def ascii_upper(s):
    s = s.replace("ı", "i").replace("İ", "I")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).upper()


def classify(text):
    norm = ascii_upper(text)
    for key, words in RULES:
        if all(w in norm for w in words):
            return key
    return None


def parse(lines):
    """Return raw entries: year heading, regex match, and following text lines."""
    raw, year, cur = [], None, None
    for line in lines:
        ym = YEAR_RE.match(line)
        if ym:
            year, cur = int(ym.group(1)), None
            continue
        if year is None:
            continue
        if line.lower().startswith(END_MARKERS):
            break
        m = DATE_RE.match(line)
        if m and m.group(4).upper() in MONTHS and (m.group(2) is None or m.group(2).upper() in MONTHS):
            cur = {"heading": year, "line": line, "m": m, "text": [m.group(6).strip()]}
            raw.append(cur)
        elif cur is not None:
            cur["text"].append(line)
    return raw


def to_events(raw):
    events, problems, seen = [], [], set()
    for r in raw:
        m = r["m"]
        d1, d2, year = int(m.group(1)), m.group(3), int(m.group(5))
        month2 = MONTHS[m.group(4).upper()]
        month1 = MONTHS[m.group(2).upper()] if m.group(2) else month2
        try:
            end = dt.date(year, month2, int(d2)) if d2 else dt.date(year, month2, d1)
            start = dt.date(year, month1, d1) if d2 else end
            if d2 and not m.group(2) and int(d2) < d1:  # "29. – 01. Mai" = 29 April to 1 May
                start = dt.date(year if month2 > 1 else year - 1, month2 - 1 or 12, d1)
        except ValueError as e:
            problems.append(f"invalid date in '{r['line']}': {e}")
            continue
        if end < start:
            problems.append(f"range ends before it starts: '{r['line']}'")
            continue
        if year != r["heading"]:
            problems.append(f"'{r['line']}' is listed under year {r['heading']}")
        text = " ".join(t for t in r["text"] if t)
        key = classify(text)
        if key is None:
            problems.append(f"unknown event '{text}' on {start} (add a rule + catalog entry)")
            continue
        eid = f"{start.year}-{key}"
        if eid in seen:
            problems.append(f"duplicate event {eid} ('{r['line']}'), skipped")
            continue
        seen.add(eid)
        events.append({"id": eid, "key": key, "start": start.isoformat(), "end": end.isoformat()})
    return events, problems


def check_order(events):
    """Within each year the source lists events chronologically; out-of-order dates are usually typos."""
    warnings = []
    by_year = {}
    for e in events:
        by_year.setdefault(e["id"][:4], []).append(e)
    for year, evs in by_year.items():
        for prev, cur in zip(evs, evs[1:]):
            if cur["start"] < prev["start"]:
                warnings.append(
                    f"{year}: dates go backwards between {prev['id']} ({prev['start']}) "
                    f"and {cur['id']} ({cur['start']}), possible typo in the source"
                )
    return warnings


def validate_overrides(overrides, catalog):
    """Catch typos in overrides.json early, with a readable message instead of a traceback."""
    errors = []
    def date_ok(v):
        try:
            dt.date.fromisoformat(v)
            return True
        except (TypeError, ValueError):
            return False
    for add in overrides.get("add", []):
        eid = add.get("id", "?")
        for k in ("id", "key", "start", "end"):
            if k not in add:
                errors.append(f"add {eid}: field '{k}' missing")
        if add.get("key") and add["key"] not in catalog["events"]:
            errors.append(f"add {eid}: unknown key '{add['key']}' (see catalog.json)")
        for k in ("start", "end"):
            if k in add and not date_ok(add[k]):
                errors.append(f"add {eid}: {k} '{add[k]}' is not YYYY-MM-DD")
        if date_ok(add.get("start")) and date_ok(add.get("end")) and add["end"] < add["start"]:
            errors.append(f"add {eid}: end before start")
    for eid, fix in overrides.get("fix", {}).items():
        for k in ("start", "end"):
            if k in fix and not date_ok(fix[k]):
                errors.append(f"fix {eid}: {k} '{fix[k]}' is not YYYY-MM-DD")
        if "key" in fix and fix["key"] not in catalog["events"]:
            errors.append(f"fix {eid}: unknown key '{fix['key']}'")
    if errors:
        raise SystemExit("ERROR in data/overrides.json:\n  " + "\n  ".join(errors))


def apply_overrides(events, overrides):
    """Manual data always wins over scraped data. overrides.json is only read here, never written."""
    events = [dict(e) for e in events]
    remove = set(overrides.get("remove", []))
    events = [e for e in events if e["id"] not in remove]
    by_id = {e["id"]: e for e in events}
    for eid, fix in overrides.get("fix", {}).items():
        if eid in by_id:
            for k in ("start", "end", "key"):
                if k in fix:
                    by_id[eid][k] = fix[k]
            log(f"  override {eid}: {fix.get('reason', fix)}")
        else:
            log(f"  WARNING override for {eid} not applied (event not found)")
    for add in overrides.get("add", []):
        new = {k: add[k] for k in ("id", "key", "start", "end")}
        if add["id"] in by_id:
            old = by_id[add["id"]]
            if (old["start"], old["end"]) != (new["start"], new["end"]):
                log(f"  NOTE source now also has {add['id']} ({old['start']}..{old['end']}); keeping your manual entry ({new['start']}..{new['end']})")
            else:
                log(f"  NOTE source now also has {add['id']} with the same dates; the manual entry can be removed")
            old.update(new)
        else:
            events.append(new)
            by_id[new["id"]] = new
            log(f"  added {add['id']}")
    return events


def apply_default_length(events, catalog):
    """Some years only give the first day of a multi-day fast; extend it to the usual length."""
    for e in events:
        days = catalog["events"][e["key"]].get("days")
        if days and e["start"] == e["end"]:
            e["end"] = (dt.date.fromisoformat(e["start"]) + dt.timedelta(days=days - 1)).isoformat()
    return events


def scrape(source_url, html_file, catalog):
    raw_html = Path(html_file).read_text(encoding="utf-8") if html_file else fetch(source_url)
    raw = parse(page_lines(raw_html))
    events, problems = to_events(raw)
    unknown = {e["key"] for e in events} - set(catalog["events"])
    if unknown:
        raise ScrapeError(f"keys without catalog entry: {sorted(unknown)}")
    events = apply_default_length(events, catalog)
    for p in problems:
        log(f"  WARNING {p}")
    for w in check_order(events):
        log(f"  WARNING {w}")
    if not events:
        raise ScrapeError("no events found; the page layout probably changed")
    years = {}
    for e in events:
        years[e["id"][:4]] = years.get(e["id"][:4], 0) + 1
    log("  found " + ", ".join(f"{y}: {n} events" for y, n in sorted(years.items())))
    for y, n in years.items():
        if n < len(catalog["events"]) - 2:
            log(f"  WARNING only {n} events for {y} (expected about {len(catalog['events'])})")
    return events


# --------------------------------------------------------------------------- output

def ics_escape(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    out, cur, size = [], "", 0
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > 75:
            out.append(cur)
            cur, size = " ", 1
        cur += ch
        size += n
    out.append(cur)
    return "\r\n".join(out)


def ics_calendar(events, lang, cfg, stamp, name=None):
    """A feed (name=None) gets refresh hints for subscriptions; a single-event file does not."""
    cal_name = name or cfg["calendar_names"][lang]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{cfg['uid_domain']}//Alevi Calendar//{lang.upper()}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"NAME:{ics_escape(cal_name)}",
        f"X-WR-CALNAME:{ics_escape(cal_name)}",
        f"X-WR-CALDESC:{ics_escape('Quelle / Kaynak / Source: ' + cfg['source_url'])}",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]
    if name is None:
        lines += ["REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for e in events:
        start = dt.date.fromisoformat(e["start"])
        end = dt.date.fromisoformat(e["end"]) + dt.timedelta(days=1)  # DTEND is exclusive
        desc = [e["note"][lang]] if e["note"] else []
        if e["url"]:
            desc.append(e["url"])
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['id']}@{cfg['uid_domain']}",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
            f"DTEND;VALUE=DATE:{end:%Y%m%d}",
            f"SUMMARY:{ics_escape(e['title'][lang])}",
        ]
        if desc:
            lines.append(f"DESCRIPTION:{ics_escape(chr(10).join(desc))}")
        if e["url"]:
            lines.append(f"URL:{e['url']}")
        lines += [
            f"CATEGORIES:{ics_escape(e['category_label'][lang])}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def build(events, updated, cfg, catalog, links):
    full = []
    for e in sorted(events, key=lambda e: e["start"]):
        c = catalog["events"][e["key"]]
        url = links.get(e["id"], links.get(e["key"]))
        if url is not None and not re.match(r"^https?://", url):
            log(f"  WARNING ignoring link for {e['id']}: '{url}' is not an http(s) URL")
            url = None
        full.append({
            "id": e["id"],
            "key": e["key"],
            "year": int(e["start"][:4]),
            "start": e["start"],
            "end": e["end"],
            "category": c["category"],
            "category_label": catalog["categories"][c["category"]],
            "title": c["title"],
            "note": c["note"],
            "url": url,
            "ics": {l: f"events/{e['id']}-{l}.ics" for l in LANGS},
        })
    api = {
        "name": cfg["calendar_names"],
        "source": cfg["source_url"],
        "updated": updated,
        "languages": list(LANGS),
        "years": sorted({e["year"] for e in full}),
        "feeds": {l: f"{cfg['base_url']}abo-{l}" for l in LANGS},  # absolute short URLs (always base_url, even if the widget is loaded via a fallback host); Caddy rewrites to alevi-{l}.ics
        "categories": catalog["categories"],
        "events": full,
    }
    stamp = updated.replace("-", "").replace(":", "")[:15] + "Z"

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    write_text(DIST / "events.json", json.dumps(api, ensure_ascii=False, indent=2) + "\n")
    for lang in LANGS:
        write_text(DIST / f"alevi-{lang}.ics", ics_calendar(full, lang, cfg, stamp))
        for e in full:
            write_text(DIST / e["ics"][lang], ics_calendar([e], lang, cfg, stamp, name=e["title"][lang]))
    shutil.copy(DIST / "alevi-de.ics", DIST / "alevi.ics")

    js = (WIDGET / "alevi-calendar.js").read_text(encoding="utf-8")
    marker = "/*__ALEVI_DATA__*/null"
    if marker not in js:
        raise SystemExit("data marker missing in widget/alevi-calendar.js")
    js = js.replace(marker, json.dumps(api, ensure_ascii=False, separators=(",", ":")))
    write_text(DIST / "alevi-calendar.js", js)
    for name in ("index.html", "embed.html", ".htaccess", "_headers"):
        text = (WIDGET / name).read_text(encoding="utf-8")
        write_text(DIST / name, text.replace("{{BASE_URL}}", cfg["base_url"]))
    return full


def check_anchors(links):
    """Warn when a link points to #anchor that no longer exists on its page (e.g. after the page was re-edited)."""
    pages = {}
    for key, url in links.items():
        if url and "#" in url:
            page, anchor = url.split("#", 1)
            pages.setdefault(page, []).append((key, anchor))
    for page, items in pages.items():
        try:
            text = fetch(page)
        except Exception as e:
            log(f"  WARNING could not check anchors on {page}: {e}")
            continue
        for key, anchor in items:
            if f'id="{anchor}"' not in text:
                log(f"  WARNING link for {key}: anchor #{anchor} not found on {page}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="parse a saved HTML file instead of fetching the site")
    ap.add_argument("--strict", action="store_true", help="fail instead of using the last good data")
    ap.add_argument("--no-link-check", action="store_true", help="skip checking that #anchors in links.json still exist")
    args = ap.parse_args()

    cfg = load_json(ROOT / "config.json")
    catalog = load_json(DATA / "catalog.json")
    overrides = load_json(DATA / "overrides.json")
    links = {k: v for k, v in load_json(DATA / "links.json").items() if not k.startswith("_")}
    last = load_json(SNAPSHOT) if SNAPSHOT.exists() else None

    validate_overrides(overrides, catalog)

    # The snapshot holds the *scraped* events only. Overrides are applied on top every time,
    # also when the site is down and we fall back to the snapshot, so manual data is never lost.
    log(f"Scraping {args.html or cfg['source_url']} ...")
    try:
        scraped = scrape(cfg["source_url"], args.html, catalog)
        if last and len(scraped) < 0.8 * len(last["events"]):
            raise ScrapeError(f"only {len(scraped)} events, last good scrape had {len(last['events'])}")
    except Exception as e:  # network errors, layout changes, ...
        if args.strict or not last:
            raise SystemExit(f"ERROR: {e}")
        log(f"ERROR: {e}\n  -> using last good data from {last['scraped']}")
        scraped = last["events"]

    scraped = sorted(scraped, key=lambda e: e["start"])
    if not last or last["events"] != scraped:
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        last = {"scraped": now, "events": scraped}
        write_text(SNAPSHOT, json.dumps(last, ensure_ascii=False, indent=2) + "\n")

    events = sorted(apply_overrides(scraped, overrides), key=lambda e: e["start"])
    for w in check_order(events):
        log(f"  WARNING after overrides: {w}")

    # "updated" only moves when the published data changes (keeps iCal DTSTAMPs stable).
    published = DIST / "events.json"
    prev = load_json(published) if published.exists() else None
    plain = lambda evs: [{k: e[k] for k in ("id", "key", "start", "end")} for e in evs]
    if prev and plain(prev["events"]) == plain(events):
        updated = prev["updated"]
    else:
        updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not args.no_link_check:
        check_anchors(links)
    full = build(events, updated, cfg, catalog, links)
    n_links = sum(1 for e in full if e["url"])
    log(f"Built {len(full)} events ({n_links} with links) into {DIST}")


if __name__ == "__main__":
    main()
