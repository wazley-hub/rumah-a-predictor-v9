"""
ui_theme.py
===========
Tema visual Rumah A Predictor: rupa app mudah alih seperti aplikasi kewangan
Malaysia (kad putih bersudut bulat di atas latar biru-kelabu cerah, satu kad
utama berwarna biru tua, fon geometri, nombor besar).

Semua gaya ada di fail ini. Untuk kembali kepada rupa asal Streamlit, buang
panggilan `apply_theme()` dalam app.py. Tiada logik analisis di sini.

Reka bentuk
-----------
Warna   : Biru Rumah #1456D8, Biru Tua #0A2463, Kuning #FFC72E (hanya untuk
          hadiah pertama dan butang), latar #ECF0F8, kad #FFFFFF, teks #0D1B3A.
Fon     : Plus Jakarta Sans (400-800). Nombor guna angka lebar tetap.
Sudut   : kad utama 22px, kad biasa 18px, jubin 14px, input 12px, cip penuh.
Satu elemen utama: kad keputusan terkini berwarna biru tua. Yang lain senyap.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Iterable, List, Optional

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:"
    "wght@400;500;600;700;800&display=swap');"
)

THEME_CSS = FONT_IMPORT + """
:root {
  color-scheme: light;
  --canvas: #ECF0F8;
  --surface: #FFFFFF;
  --ink: #0D1B3A;
  --muted: #5B6B8A;
  --line: #DCE3F0;
  --blue: #1456D8;
  --navy: #0A2463;
  --sky: #E5EDFF;
  --yellow: #FFC72E;
  --green: #0E9F6E;
  --green-bg: #E3F6EE;
  --slate-bg: #EEF1F6;
  --shadow: 0 8px 24px rgba(10, 36, 99, .08);
}

/* ---------- asas ---------- */
html, body, .stApp {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
  color: var(--ink);
}
button, input, textarea, select { font-family: inherit; }
.stApp, [data-testid="stAppViewContainer"] { background: var(--canvas); }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stDecoration"], .stDeployButton { display: none !important; }
a[href^="#"] { display: none !important; }

.block-container {
  max-width: 960px;
  padding: 1.1rem 1rem 4rem;
}
h1, h2, h3, h4 { color: var(--ink); font-weight: 800; letter-spacing: -0.01em; }
h4 { font-size: 1.05rem; margin: 1.6rem 0 .5rem; }
p, li, label, .stMarkdown { line-height: 1.55; }
[data-testid="stCaptionContainer"] { color: var(--muted); }

/* ---------- kad keputusan terkini (elemen utama) ---------- */
.rh-hero {
  background: linear-gradient(135deg, #0A2463 0%, #1456D8 100%);
  color: #fff;
  border-radius: 22px;
  padding: 18px 18px 20px;
  box-shadow: 0 14px 32px rgba(10, 36, 99, .28);
  margin-bottom: 16px;
}
.rh-hero-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.rh-brand { display: flex; align-items: center; gap: 11px; }
.rh-mark {
  width: 38px; height: 38px; border-radius: 12px; background: var(--yellow); color: var(--navy);
  display: grid; place-items: center; font-weight: 800; font-size: 1.15rem;
}
.rh-title { font-weight: 800; font-size: 1.1rem; line-height: 1.2; }
.rh-sub { font-size: .8rem; opacity: .8; }
.rh-status { display: flex; gap: 6px; flex-wrap: wrap; }
.rh-pill {
  display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,.14);
  border-radius: 999px; padding: 4px 10px; font-size: .74rem; font-weight: 600;
}
.rh-dot { width: 7px; height: 7px; border-radius: 50%; background: #5BF0B0; display: inline-block; }
.rh-draw { display: flex; justify-content: space-between; align-items: flex-end; margin: 18px 2px 10px; gap: 10px; }
.rh-draw small { display: block; font-size: .74rem; font-weight: 600; opacity: .8; }
.rh-draw b { font-size: 1.05rem; font-weight: 800; }
.rh-draw span { font-size: .8rem; opacity: .85; white-space: nowrap; }
.rh-prizes { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.rh-prize {
  background: rgba(255,255,255,.12); border-radius: 14px; padding: 11px 8px 12px; text-align: center;
}
.rh-prize small { display: block; font-size: .74rem; font-weight: 600; opacity: .85; margin-bottom: 2px; }
.rh-prize strong {
  display: block; font-size: 1.95rem; font-weight: 800; letter-spacing: .04em;
  font-variant-numeric: tabular-nums; line-height: 1.15;
}
.rh-prize.first { background: var(--yellow); color: var(--navy); }
.rh-prize.first small { opacity: .75; }

/* ---------- kad umum ---------- */
.rh-card {
  background: var(--surface); border: 1px solid var(--line); border-radius: 18px;
  padding: 16px 16px 14px; box-shadow: var(--shadow); margin: 0 0 16px;
}
.rh-card-title { font-weight: 800; font-size: 1.02rem; }
.rh-card-sub { color: var(--muted); font-size: .82rem; margin-top: 2px; }
.rh-foot { color: var(--muted); font-size: .8rem; margin-top: 10px; }

/* ---------- baris asal nombor ---------- */
.rh-row {
  display: grid; grid-template-columns: 44px 84px 1fr; gap: 10px; align-items: center;
  padding: 11px 0; border-top: 1px solid var(--line);
}
.rh-card-head + .rh-row { margin-top: 10px; }
.rh-rank { font-size: .78rem; font-weight: 700; color: var(--muted); }
.rh-num { font-size: 1.35rem; font-weight: 800; letter-spacing: .05em; font-variant-numeric: tabular-nums; }
.rh-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.rh-chip {
  border-radius: 999px; padding: 4px 11px; font-size: .78rem; font-weight: 600;
  background: var(--green-bg); color: #08724F;
}
.rh-chip.none { background: var(--slate-bg); color: var(--muted); }
.rh-route { grid-column: 3; color: var(--muted); font-size: .76rem; margin-top: -2px; }

/* ---------- ringkasan signal ---------- */
.rh-signals { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 8px 0 12px; }
.rh-sig {
  background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 12px 12px 11px;
}
.rh-sig-label { color: var(--muted); font-size: .76rem; font-weight: 600; }
.rh-sig-value { font-size: 1.45rem; font-weight: 800; margin: 2px 0 0; color: var(--navy); line-height: 1.15; }
.rh-sig-kind { font-size: .8rem; font-weight: 600; color: var(--blue); margin: 0 0 8px; }
.rh-sig.none .rh-sig-value { color: var(--line); }
.rh-sig.none .rh-sig-kind { color: var(--muted); }
.rh-dots { display: flex; gap: 4px; }
.rh-dots i { width: 18px; height: 5px; border-radius: 3px; background: var(--line); display: block; }
.rh-dots i.on { background: var(--blue); }
.rh-sig-note { color: var(--muted); font-size: .72rem; margin-top: 5px; }
.rh-infos { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.rh-info { background: var(--sky); border-radius: 12px; padding: 7px 12px; font-size: .84rem; }
.rh-info span { color: var(--muted); font-weight: 600; margin-right: 6px; }
.rh-info b { color: var(--navy); font-weight: 800; }

/* ---------- tajuk bahagian (kelas lama dikekalkan) ---------- */
.rap-panel-title { font-size: 1.05rem; font-weight: 800; color: var(--ink); margin: 1.5rem 0 .5rem; }
.rap-section-kicker {
  font-size: .9rem; font-weight: 700; color: var(--muted); margin: 2.4rem 0 .6rem;
  padding-top: 1.1rem; border-top: 1px solid var(--line);
}
.engine-head {
  font-size: .95rem; font-weight: 800; color: var(--navy); background: var(--sky);
  border-radius: 12px; padding: 9px 14px; margin: 1.3rem 0 .6rem; border-left: 5px solid var(--blue);
}
.engine-head.engine-v2 { border-left-color: var(--green); }
.engine-head.engine-chart { border-left-color: var(--yellow); }
.rap-badge { font-size: .75rem; font-weight: 600; }

/* ---------- komponen Streamlit ---------- */
/* Tab: selektor tidak bergantung pada kelas .stTabs supaya sah dalam pelbagai versi Streamlit */
[data-baseweb="tab-list"], [role="tablist"] {
  gap: 4px !important; background: #DEE6F4 !important; padding: 4px !important;
  border-radius: 16px !important; border: 0 !important; box-shadow: none !important;
}
button[data-baseweb="tab"], button[role="tab"] {
  height: 40px !important; padding: 0 14px !important; border-radius: 12px !important;
  font-weight: 600 !important; color: var(--muted) !important; background: transparent !important;
  border: 0 !important; margin: 0 !important; overflow: hidden;
  white-space: nowrap !important; flex: 0 0 auto;
}
button[role="tab"] p, button[data-baseweb="tab"] p { white-space: nowrap !important; margin: 0 !important; }
button[data-baseweb="tab"]:hover, button[role="tab"]:hover { background: rgba(255,255,255,.55) !important; color: var(--navy) !important; }
button[data-baseweb="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] {
  background: var(--surface) !important; color: var(--blue) !important; box-shadow: 0 2px 8px rgba(10,36,99,.14) !important;
}
button[role="tab"] p, button[data-baseweb="tab"] p { font-weight: 700 !important; font-size: .9rem !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
[data-baseweb="tab-panel"] { padding-top: 1rem !important; }

[data-testid="stExpander"], [data-testid="stExpander"] details {
  background: var(--surface) !important; border: 1px solid var(--line) !important; border-radius: 14px !important;
  overflow: hidden; margin-bottom: 8px;
}
[data-testid="stExpander"] summary { font-weight: 600; }

[data-testid="stForm"] {
  background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 16px;
  box-shadow: var(--shadow);
}
[data-testid="stForm"] input {
  text-align: center; font-size: 1.35rem; font-weight: 800; letter-spacing: .2em;
  font-variant-numeric: tabular-nums; border-radius: 12px;
}

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px !important; font-weight: 700; border: 1px solid var(--line); min-height: 44px;
  background: var(--surface); color: var(--navy);
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--blue); color: var(--blue); }
[data-testid="stFormSubmitButton"] > button {
  width: 100%; min-height: 50px; font-size: 1.02rem; background: var(--blue); color: #fff; border: 0;
  box-shadow: 0 8px 18px rgba(20, 86, 216, .3);
}
[data-testid="stFormSubmitButton"] > button:hover { background: #0F47B8; color: #fff; }

[data-baseweb="select"] > div, .stTextInput input, [data-baseweb="input"], [data-baseweb="base-input"] { border-radius: 12px !important; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; margin-bottom: .8rem; }
[data-testid="stCode"] pre, [data-testid="stCode"] code {
  background: #F0F5FF !important; color: var(--navy) !important; font-weight: 700; letter-spacing: .06em;
  white-space: pre-wrap !important; word-break: break-word;
}
[data-testid="stCode"] { border: 1px solid #D6E3FF; border-radius: 12px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stMetric"] {
  background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px;
}
[data-testid="stMetricValue"] { font-weight: 800; color: var(--navy); font-variant-numeric: tabular-nums; }
[data-testid="stMetricLabel"] { color: var(--muted); }

@media (max-width: 640px) {
  .block-container { padding-left: .7rem; padding-right: .7rem; }
  button[data-baseweb="tab"], button[role="tab"] { padding: 0 9px !important; height: 38px !important; }
  button[role="tab"] p, button[data-baseweb="tab"] p { font-size: .78rem !important; }
  [data-baseweb="tab-list"], [role="tablist"] { gap: 2px !important; overflow-x: auto; }
  .rh-prize strong { font-size: 1.55rem; }
  .rh-row { grid-template-columns: 38px 74px 1fr; gap: 8px; }
  .rh-num { font-size: 1.2rem; }
  .rh-signals { gap: 8px; }
  .rh-sig-value { font-size: 1.25rem; }
}
"""

_MONTHS = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogo", "Sep", "Okt", "Nov", "Dis"]


def apply_theme(st) -> None:
    """Suntik CSS tema. Panggil sekali selepas st.set_page_config."""
    st.markdown(f"<style>{THEME_CSS}</style>", unsafe_allow_html=True)


def _e(value) -> str:
    return html.escape(str(value), quote=True)


def format_draw_date(value) -> str:
    """20261025 -> 25 Okt 2026. Jika format tidak dikenali, kembalikan teks asal."""
    text = str(value).strip().split(".")[0]
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            d = datetime.strptime(text[:10] if "-" in fmt or "/" in fmt else text[:8], fmt)
            return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"
        except ValueError:
            continue
    return text


def hero_html(draw_no, draw_date, first, second, third,
              sync_active: bool = False, source: str = "") -> str:
    """Kad utama: keputusan terkini dengan tiga hadiah, status sambungan di atas."""
    pills = []
    if sync_active:
        pills.append('<span class="rh-pill"><i class="rh-dot"></i>GitHub aktif</span>')
    else:
        pills.append('<span class="rh-pill">GitHub belum diset</span>')
    if source:
        pills.append(f'<span class="rh-pill">Sumber: {_e(source)}</span>')
    return (
        '<div class="rh-hero">'
        '<div class="rh-hero-top">'
        '<div class="rh-brand"><div class="rh-mark">R</div>'
        '<div><div class="rh-title">Rumah A Predictor</div>'
        '<div class="rh-sub">Analisis corak nombor Top 3</div></div></div>'
        f'<div class="rh-status">{"".join(pills)}</div>'
        '</div>'
        f'<div class="rh-draw"><div><small>Keputusan terkini</small><b>Draw {_e(draw_no)}</b></div>'
        f'<span>{_e(format_draw_date(draw_date))}</span></div>'
        '<div class="rh-prizes">'
        f'<div class="rh-prize first"><small>1st</small><strong>{_e(first)}</strong></div>'
        f'<div class="rh-prize"><small>2nd</small><strong>{_e(second)}</strong></div>'
        f'<div class="rh-prize"><small>3rd</small><strong>{_e(third)}</strong></div>'
        '</div></div>'
    )


def origin_html(rows: Iterable[dict], source_draw, source_result, summary: str) -> str:
    """
    Kad "Nombor terkini naik daripada mana".
    rows: [{"Hadiah","No","Dijana oleh","Laluan"}]; "Tiada engine menjana" dipaparkan kelabu.
    """
    body = []
    for r in rows:
        engines = str(r.get("Dijana oleh", ""))
        if engines.startswith("Tiada"):
            chips = f'<span class="rh-chip none">{_e(engines)}</span>'
        else:
            chips = "".join(f'<span class="rh-chip">{_e(x.strip())}</span>' for x in engines.split(",") if x.strip())
        route = str(r.get("Laluan", "-"))
        route_html = ""
        if route not in ("-", "", "nan"):
            parts = [p.strip() for p in route.split(" | ") if p.strip()]
            shown = " | ".join(parts[:3]) + (f"  (+{len(parts) - 3} lagi)" if len(parts) > 3 else "")
            route_html = f'<div class="rh-route">{_e(shown)}</div>'
        body.append(
            '<div class="rh-row">'
            f'<div class="rh-rank">{_e(r.get("Hadiah", ""))}</div>'
            f'<div class="rh-num">{_e(r.get("No", ""))}</div>'
            f'<div class="rh-chips">{chips}</div>{route_html}</div>'
        )
    return (
        '<div class="rh-card">'
        '<div class="rh-card-head"><div class="rh-card-title">Nombor terkini naik daripada mana</div>'
        f'<div class="rh-card-sub">Ramalan daripada draw {_e(source_draw)}, hasil {_e(source_result)}</div></div>'
        f'{"".join(body)}'
        f'<div class="rh-foot">{_e(summary)}</div></div>'
    )


def signal_tiles_html(items: List[dict]) -> str:
    """items: [{"label","value","kind","support"(0-4),"none"(bool)}] -> tiga jubin signal."""
    tiles = []
    for it in items:
        support = max(0, min(4, int(it.get("support", 0))))
        dots = "".join(f'<i class="{"on" if i < support else ""}"></i>' for i in range(4))
        cls = "rh-sig none" if it.get("none") else "rh-sig"
        tiles.append(
            f'<div class="{cls}"><div class="rh-sig-label">{_e(it.get("label", ""))}</div>'
            f'<div class="rh-sig-value">{_e(it.get("value", ""))}</div>'
            f'<div class="rh-sig-kind">{_e(it.get("kind", ""))}</div>'
            f'<div class="rh-dots">{dots}</div>'
            f'<div class="rh-sig-note">Sokongan {support}/4</div></div>'
        )
    return f'<div class="rh-signals">{"".join(tiles)}</div>'


def info_row_html(pairs: List[tuple]) -> str:
    """pairs: [("Bridge","V1"),("Laluan","Triple Match V1")]"""
    cells = "".join(f'<div class="rh-info"><span>{_e(k)}</span><b>{_e(v)}</b></div>' for k, v in pairs)
    return f'<div class="rh-infos">{cells}</div>'
