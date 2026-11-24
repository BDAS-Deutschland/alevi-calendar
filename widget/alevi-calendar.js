/*! Alevi calendar widget · kalender.bdas.de · data: aabf-inanc-kurulu.com */
(function () {
  "use strict";
  if (!window.customElements || customElements.get("alevi-calendar")) return;

  var DATA = /*__ALEVI_DATA__*/null;
  var SRC = document.currentScript && document.currentScript.src;
  var BASE = new URL(".", SRC || location.href).href;
  var LANGS = ["de", "tr", "en"];
  var LOCALES = { de: "de-DE", tr: "tr-TR", en: "en-GB" };

  var T = {
    de: {
      subscribe: "Abonnieren", download: "Herunterladen",
      next: "Als Nächstes", today: "Heute", source: "Quelle",
      hint: "Abonnierte Termine bleiben automatisch aktuell.",
      apple: "Apple Kalender (iPhone, Mac)", google: "Google Kalender", outlook: "Outlook",
      copy: "Link kopieren (andere Apps)", copied: "Link kopiert!", copyPrompt: "Kalender-Link kopieren:",
      prev: "Vorheriges Jahr", nextYear: "Nächstes Jahr", lang: "Sprache", open: "Mehr erfahren",
      none: "Keine Termine."
    },
    tr: {
      subscribe: "Abone ol", download: "İndir",
      next: "Sıradaki", today: "Bugün", source: "Kaynak",
      hint: "Abone olunan etkinlikler otomatik olarak güncellenir.",
      apple: "Apple Takvim (iPhone, Mac)", google: "Google Takvim", outlook: "Outlook",
      copy: "Bağlantıyı kopyala (diğer uygulamalar)", copied: "Bağlantı kopyalandı!", copyPrompt: "Takvim bağlantısını kopyalayın:",
      prev: "Önceki yıl", nextYear: "Sonraki yıl", lang: "Dil", open: "Daha fazla bilgi",
      none: "Etkinlik yok."
    },
    en: {
      subscribe: "Subscribe", download: "Download",
      next: "Up next", today: "Today", source: "Source",
      hint: "Subscribed events stay up to date automatically.",
      apple: "Apple Calendar (iPhone, Mac)", google: "Google Calendar", outlook: "Outlook",
      copy: "Copy link (other apps)", copied: "Link copied!", copyPrompt: "Copy the calendar link:",
      prev: "Previous year", nextYear: "Next year", lang: "Language", open: "Learn more",
      none: "No dates."
    }
  };

  var ICON = {
    left: '<path d="M15 18l-6-6 6-6"/>',
    right: '<path d="M9 18l6-6-6-6"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    bell: '<path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 003.4 0"/>',
    down: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
    link: '<path d="M10 13a5 5 0 007.07 0l3-3a5 5 0 00-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 00-7.07 0l-3 3a5 5 0 007.07 7.07l1.5-1.5"/>',
    cal: '<rect x="3" y="4.5" width="18" height="16" rx="2.5"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>'
  };
  function icon(name, size) {
    return '<svg aria-hidden="true" width="' + (size || 18) + '" height="' + (size || 18) +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      ICON[name] + "</svg>";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function httpUrl(u) {
    try { var x = new URL(u, BASE); return /^https?:$/.test(x.protocol) ? x.href : null; } catch (e) { return null; }
  }
  function day(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function today() { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }

  function fmtRange(lang, s, e) {
    var f = new Intl.DateTimeFormat(LOCALES[lang], { weekday: "short", day: "numeric", month: "long" });
    if (+s === +e) return f.format(s);
    if (f.formatRange) { try { return f.formatRange(s, e); } catch (x) { /* fall through */ } }
    return f.format(s) + " – " + f.format(e);
  }
  function monthShort(lang, d) {
    return new Intl.DateTimeFormat(LOCALES[lang], { month: "short" }).format(d).replace(/\.$/, "");
  }

  function feeds(lang) {
    var https = new URL(DATA.feeds[lang], BASE).href;
    var webcal = https.replace(/^https?:/, "webcal:");
    var name = DATA.name[lang];
    return {
      https: https,
      // /download-xx is served with Content-Disposition: attachment (the download attribute is ignored cross-origin)
      download: /\/abo(-[a-z]+)?$/.test(https) ? https.replace(/\/abo(-[a-z]+)?$/, "/download$1") : https,
      apple: webcal,
      google: "https://calendar.google.com/calendar/r?cid=" + encodeURIComponent(webcal),
      outlook: "https://outlook.live.com/calendar/0/addfromweb?url=" + encodeURIComponent(https) +
        "&name=" + encodeURIComponent(name)
    };
  }

  var CSS = [
    ":host{all:initial;display:block;container-type:inline-size}",
    ":host([hidden]){display:none}",
    "*,*::before,*::after{box-sizing:border-box}",
    ".cal{--a:var(--alevi-accent,#cc2d1d);--tx:var(--alevi-text,#68686b);--bg:var(--alevi-bg,#fff);--soft:var(--alevi-soft,#fbefee);--line:#e9e9eb;--hover:#fbf7f7;",
    "font-family:var(--alevi-font,system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif);font-size:15px;line-height:1.45;color:var(--tx);",
    "background:var(--bg);border:1px solid var(--line);border-radius:18px;box-shadow:0 1px 2px rgba(40,40,44,.04),0 10px 30px rgba(40,40,44,.07);position:relative;-webkit-font-smoothing:antialiased}",
    "button{font:inherit;color:inherit}",
    ":focus{outline:none}:focus-visible{outline:2px solid var(--a);outline-offset:2px}",

    ".hd{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px 16px;padding:20px 22px 16px;border-bottom:1px solid var(--line)}",
    ".kicker{margin:0 0 6px;font-size:12px;font-weight:650;letter-spacing:.09em;text-transform:uppercase;color:var(--tx);display:flex;align-items:center;gap:7px}",
    ".kicker svg{color:var(--a)}",
    ".yr{display:flex;align-items:center;gap:8px}",
    ".yr h2{margin:0;font-size:30px;line-height:1;font-weight:750;color:var(--a);font-variant-numeric:tabular-nums;letter-spacing:-.01em}",
    ".ib{appearance:none;width:32px;height:32px;border-radius:50%;border:1px solid var(--line);background:var(--bg);color:var(--tx);display:grid;place-items:center;cursor:pointer;transition:border-color .15s,color .15s,background .15s}",
    ".ib:hover:not(:disabled){border-color:var(--a);color:var(--a);background:var(--soft)}",
    ".ib:disabled{opacity:.3;cursor:default}",
    ".ctl{display:flex;flex-wrap:wrap;gap:8px}",
    ".langs{display:inline-flex;gap:2px;padding:3px;border:1px solid var(--line);border-radius:999px;background:var(--bg)}",
    ".langs button{appearance:none;border:0;background:transparent;padding:5px 11px;border-radius:999px;font-size:12px;font-weight:700;letter-spacing:.05em;cursor:pointer;color:var(--tx);transition:background .15s,color .15s}",
    ".langs button:hover{color:var(--a)}",
    ".langs button[aria-pressed=true]{background:var(--a);color:#fff}",

    ".list{list-style:none;margin:0;padding:6px 0}",
    ".ev{position:relative;display:flex;align-items:stretch}",
    ".ev+.ev::after{content:'';position:absolute;top:0;left:22px;right:22px;border-top:1px solid var(--line)}",
    ".main{flex:1;min-width:0;display:flex;align-items:center;gap:15px;padding:13px 16px 13px 22px;color:inherit;text-decoration:none;border-radius:12px;transition:background .15s}",
    "a.main{cursor:pointer}a.main:hover{background:var(--hover)}",
    ".main:focus-visible{outline-offset:-2px}",
    ".badge{flex:none;width:56px;height:56px;border-radius:14px;background:var(--soft);color:var(--a);display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;transition:transform .15s}",
    "a.main:hover .badge{transform:scale(1.04)}",
    ".badge .d{font-size:20px;font-weight:750;font-variant-numeric:tabular-nums;letter-spacing:-.02em}",
    ".badge .d.r{font-size:14.5px}",
    ".badge .m{margin-top:4px;font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}",
    ".body{min-width:0;display:flex;flex-direction:column;gap:3px}",
    ".meta{display:flex;flex-wrap:wrap;align-items:center;gap:3px 10px;font-size:12.5px}",
    ".title{font-size:15.5px;font-weight:650;line-height:1.3;color:var(--tx)}",
    "a.main:hover .title{color:var(--a)}",
    ".note{font-size:13px;opacity:.85}",
    ".cat{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}",
    ".cat::before{content:'';width:7px;height:7px;border-radius:50%;background:var(--tx)}",
    ".cat.fasten::before{background:var(--a)}",
    ".cat.fest::before{background:transparent;box-shadow:inset 0 0 0 1.6px var(--a)}",
    ".flag{font-size:10.5px;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:#fff;background:var(--a);padding:2px 8px;border-radius:999px}",
    ".more{display:inline-flex;align-items:center;gap:5px;margin-top:3px;font-size:13.5px;font-weight:650;color:var(--a)}",
    ".more svg{transition:transform .15s}",
    "a.main:hover .more{text-decoration:underline;text-underline-offset:3px}a.main:hover .more svg{transform:translateX(3px)}",
    ".ev.past .main{opacity:.45}",
    ".ev.next .badge{background:var(--a);color:#fff;box-shadow:0 6px 16px -6px var(--a)}",
    ".ev.next::before{content:'';position:absolute;left:0;top:14px;bottom:14px;width:3px;border-radius:0 3px 3px 0;background:var(--a)}",

    ".ft{position:relative;display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:16px 22px 18px;border-top:1px solid var(--line);background:#fafafa;border-radius:0 0 18px 18px}",
    ".btn{appearance:none;display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:9px 17px;border-radius:999px;border:1.5px solid var(--a);font-size:14px;font-weight:650;line-height:1.2;text-decoration:none;cursor:pointer;transition:background .15s,filter .15s}",
    ".btn.pri{background:var(--a);color:#fff}.btn.pri:hover{filter:brightness(.9)}",
    ".btn.sec{background:var(--bg);color:var(--a)}.btn.sec:hover{background:var(--soft)}",
    ".credit{margin-left:auto;font-size:12px}.credit a{color:inherit;text-underline-offset:2px}.credit a:hover{color:var(--a)}",
    ".menu{position:absolute;left:16px;bottom:calc(100% - 8px);z-index:10;width:min(320px,calc(100% - 32px));padding:8px;background:var(--bg);border:1px solid var(--line);border-radius:16px;box-shadow:0 18px 40px rgba(40,40,44,.18)}",
    ".menu[hidden]{display:none}",
    ".menu p{margin:6px 10px 8px;font-size:12.5px}",
    ".menu a,.menu button{display:flex;align-items:center;gap:11px;width:100%;padding:10px;border:0;border-radius:10px;background:none;color:var(--tx);font-size:14px;font-weight:550;text-align:left;text-decoration:none;cursor:pointer}",
    ".menu a:hover,.menu button:hover{background:var(--soft);color:var(--a)}",
    ".menu svg{flex:none;color:var(--a)}",
    ".menu input.url{display:block;box-sizing:border-box;width:100%;margin:6px 0 2px;padding:8px 10px;border:1px solid var(--line);border-radius:10px;font:inherit;font-size:13px;color:var(--tx);background:var(--soft)}",
    ".empty{padding:28px 22px;margin:0;text-align:center}",

    "@container (max-width:460px){",
    ".hd{padding:16px 16px 14px}.yr h2{font-size:26px}",
    ".ev+.ev::after{left:16px;right:16px}",
    ".main{gap:12px;padding:12px 12px 12px 16px}.badge{width:50px;height:50px;border-radius:12px}",
    
    ".ft{padding:14px 16px 16px}.ft .btn{flex:1 1 140px}.credit{margin:2px 0 0;width:100%;text-align:center}",
    "}",
    "@media (prefers-reduced-motion:reduce){*{transition:none!important}}"
  ].join("");

  function pickLang(el) {
    var c = [el.getAttribute("lang"), document.documentElement.lang, navigator.language];
    for (var i = 0; i < c.length; i++) {
      var l = (c[i] || "").slice(0, 2).toLowerCase();
      if (LANGS.indexOf(l) >= 0) return l;
    }
    return "de";
  }
  function pickYear(attr, years, nextYear) {
    var y = parseInt(attr, 10);
    if (years.indexOf(y) >= 0) return y;
    if (nextYear && years.indexOf(nextYear) >= 0) return nextYear; // year of the next upcoming event
    var now = new Date().getFullYear();
    if (years.indexOf(now) >= 0) return now;
    for (var i = 0; i < years.length; i++) if (years[i] > now) return years[i];
    return years[years.length - 1];
  }

  class AleviCalendar extends HTMLElement {
    static get observedAttributes() { return ["lang", "year", "target"]; }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._lang = null;
      this._year = null;
      this._menu = false;
      var self = this;
      this.shadowRoot.addEventListener("click", function (e) { self._onClick(e); });
      this._outside = function (e) { if (self._menu && e.composedPath().indexOf(self) < 0) self._setMenu(false); };
      this._esc = function (e) {
        if (e.key === "Escape" && self._menu) { self._setMenu(false); self._focus('[data-action="menu"]'); }
      };
    }
    connectedCallback() {
      document.addEventListener("click", this._outside);
      document.addEventListener("keydown", this._esc);
      this.render();
    }
    disconnectedCallback() {
      document.removeEventListener("click", this._outside);
      document.removeEventListener("keydown", this._esc);
    }
    attributeChangedCallback(name) {
      if (name === "lang") this._lang = null;
      if (name === "year") this._year = null;
      if (this.isConnected) this.render();
    }

    _focus(sel) { var el = this.shadowRoot.querySelector(sel); if (el && !el.disabled) el.focus(); }

    _setMenu(open) {
      this._menu = open;
      var m = this.shadowRoot.querySelector(".menu");
      var b = this.shadowRoot.querySelector('[data-action="menu"]');
      if (m) m.hidden = !open;
      if (b) b.setAttribute("aria-expanded", String(open));
    }

    _onClick(e) {
      var b = e.target.closest("[data-action]");
      if (!b) return;
      var a = b.getAttribute("data-action"), years = DATA.years, i = years.indexOf(this._year);
      if (a === "prev" && i > 0) { this._year = years[i - 1]; this._rerender('[data-action="prev"]'); }
      else if (a === "next" && i < years.length - 1) { this._year = years[i + 1]; this._rerender('[data-action="next"]'); }
      else if (a === "lang") { this._lang = b.getAttribute("data-lang"); this._rerender('[data-lang="' + this._lang + '"]'); }
      else if (a === "menu") { this._setMenu(!this._menu); }
      else if (a === "copy") { this._copy(b); }
    }

    _rerender(focusSel) { this._menu = false; this.render(); this._focus(focusSel); }

    _copy(btn) {
      var t = T[this._lang], url = feeds(this._lang).https, label = btn.querySelector(".lbl");
      var done = function () {
        label.textContent = t.copied;
        setTimeout(function () { label.textContent = t.copy; }, 1800);
      };
      // Fallback for iframes without clipboard permission: show the link in a field and try execCommand.
      var menu = this.shadowRoot.querySelector(".menu");
      var fallback = function () {
        var inp = menu.querySelector("input.url");
        if (!inp) {
          inp = document.createElement("input");
          inp.className = "url"; inp.readOnly = true; inp.value = url; inp.setAttribute("aria-label", t.copyPrompt);
          menu.appendChild(inp);
        }
        inp.focus(); inp.select();
        try { if (document.execCommand("copy")) done(); } catch (x) { /* link stays visible for manual copying */ }
      };
      if (navigator.clipboard && window.isSecureContext) {
        try { navigator.clipboard.writeText(url).then(done, fallback); } catch (x) { fallback(); }
      } else fallback();
    }

    render() {
      var root = this.shadowRoot;
      if (!DATA || !DATA.events || !DATA.events.length) {
        root.innerHTML = "<style>" + CSS + "</style><div class='cal'><p class='empty'>–</p></div>";
        return;
      }
      var lang = this._lang || (this._lang = pickLang(this));
      // Inside an iframe (e.g. a website builder), iOS Safari/Chrome ignore a normal tap on download/webcal links;
      // opening them in a new top-level tab works (same as "long-press -> open").
      var framed = false; try { framed = window.top !== window.self; } catch (x) { framed = true; }
      var ext = framed ? ' target="_blank" rel="noopener"' : "";
      var now = today(), nextId = null, nextYear = null;
      for (var k = 0; k < DATA.events.length; k++) {
        if (day(DATA.events[k].end) >= now) { nextId = DATA.events[k].id; nextYear = DATA.events[k].year; break; }
      }
      if (this._year == null) this._year = pickYear(this.getAttribute("year"), DATA.years, nextYear);
      var t = T[lang], year = this._year, yi = DATA.years.indexOf(year);
      var target = this.getAttribute("target") || "_self";
      var rel = target === "_blank" ? ' rel="noopener"' : "";

      var list = DATA.events.filter(function (e) { return e.year === year; });

      var items = list.map(function (e) {
        var s = day(e.start), en = day(e.end), url = e.url && httpUrl(e.url);
        var range = +s !== +en;
        var isToday = s <= now && now <= en, past = en < now, isNext = e.id === nextId;
        var cls = "ev" + (past ? " past" : "") + (isNext ? " next" : "");
        var flag = isToday ? t.today : isNext ? t.next : "";
        var inner =
          '<span class="badge" aria-hidden="true"><span class="d' + (range ? " r" : "") + '">' +
          s.getDate() + (range ? "–" + en.getDate() : "") + '</span><span class="m">' + esc(monthShort(lang, s)) + "</span></span>" +
          '<span class="body"><span class="meta"><time datetime="' + e.start + '">' + esc(fmtRange(lang, s, en)) + "</time>" +
          '<span class="cat ' + esc(e.category) + '">' + esc(e.category_label[lang]) + "</span>" +
          (flag ? '<span class="flag">' + esc(flag) + "</span>" : "") + "</span>" +
          '<span class="title">' + esc(e.title[lang]) + "</span>" +
          (e.note ? '<span class="note">' + esc(e.note[lang]) + "</span>" : "") +
          (url ? '<span class="more">' + esc(t.open) + icon("arrow", 15) + "</span>" : "") + "</span>";
        var main = url
          ? '<a class="main" href="' + esc(url) + '" target="' + esc(target) + '"' + rel + ">" + inner + "</a>"
          : '<div class="main">' + inner + "</div>";
        return '<li class="' + cls + '"' + (isNext ? ' aria-current="date"' : "") + ">" + main + "</li>";
      }).join("");

      var f = feeds(lang);
      var langBtns = LANGS.map(function (l) {
        return '<button type="button" data-action="lang" data-lang="' + l + '" aria-pressed="' + (l === lang) + '" lang="' + l + '">' +
          l.toUpperCase() + "</button>";
      }).join("");

      root.innerHTML =
        "<style>" + CSS + "</style>" +
        '<section class="cal" lang="' + lang + '" aria-label="' + esc(DATA.name[lang] + " " + year) + '">' +
        '<header class="hd"><div>' +
        '<p class="kicker">' + icon("cal", 15) + esc(DATA.name[lang]) + "</p>" +
        ('<div class="yr"><button type="button" class="ib" data-action="prev" aria-label="' + esc(t.prev) + '"' + (yi <= 0 ? " disabled" : "") + ">" + icon("left") + "</button>" +
            '<h2 aria-live="polite">' + year + "</h2>" +
            '<button type="button" class="ib" data-action="next" aria-label="' + esc(t.nextYear) + '"' + (yi >= DATA.years.length - 1 ? " disabled" : "") + ">" + icon("right") + "</button></div>") +
        "</div>" +
        '<div class="ctl"><div class="langs" role="group" aria-label="' + esc(t.lang) + '">' + langBtns + "</div></div></header>" +
        (items ? '<ol class="list">' + items + "</ol>" : '<p class="empty">' + esc(t.none) + "</p>") +
        '<footer class="ft">' +
        '<button type="button" class="btn pri" data-action="menu" aria-haspopup="true" aria-expanded="false">' + icon("bell") + esc(t.subscribe) + "</button>" +
        '<a class="btn sec" href="' + esc(f.download) + '"' + (framed ? ext : ' download="' + esc(DATA.name[lang]) + '.ics"') + '>' + icon("down") + esc(t.download) + " (.ics)</a>" +
        '<span class="credit">' + esc(t.source) + ': <a href="' + esc(DATA.source) + '" target="_blank" rel="noopener">' + esc(DATA.source.replace(/^https?:\/\/(www\.)?/, "").split("/")[0]) + '</a></span>' +
        '<div class="menu" hidden><p>' + esc(t.hint) + "</p>" +
        '<a href="' + esc(f.apple) + '"' + ext + '>' + icon("cal") + esc(t.apple) + "</a>" +
        '<a href="' + esc(f.google) + '" target="_blank" rel="noopener">' + icon("cal") + esc(t.google) + "</a>" +
        '<a href="' + esc(f.outlook) + '" target="_blank" rel="noopener">' + icon("cal") + esc(t.outlook) + "</a>" +
        '<button type="button" data-action="copy">' + icon("link") + '<span class="lbl">' + esc(t.copy) + "</span></button>" +
        "</div></footer></section>";
    }
  }

  customElements.define("alevi-calendar", AleviCalendar);
})();
