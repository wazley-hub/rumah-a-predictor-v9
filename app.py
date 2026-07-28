
import streamlit as st
import json
import streamlit.components.v1 as components
import pandas as pd
import requests
import base64
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from io import BytesIO
from selection_engine_v1 import build_selection_engine






def copy_button_clean(label, value, key_name):
    js_value = json.dumps(str(value))
    components.html(
        f"""
        <button onclick='navigator.clipboard.writeText({js_value}).then(() => {{
            const msg = document.getElementById("msg_{key_name}");
            msg.innerText = "Disalin";
            setTimeout(() => msg.innerText = "", 1600);
        }}).catch(() => {{
            const msg = document.getElementById("msg_{key_name}");
            msg.innerText = "Copy gagal. Sila salin manual dari kotak.";
        }});'
        style="border:0;border-radius:10px;background:#3157e5;color:white;padding:9px 15px;font-size:14px;font-weight:750;margin-right:8px;box-shadow:0 5px 14px rgba(49,87,229,.18);">
            {label}
        </button>
        <span id="msg_{key_name}" style="color:#15803d;font-size:14px;font-weight:700;margin-left:8px;"></span>
        """,
        height=48
    )

st.set_page_config(page_title="Rumah A Predictor", page_icon="🎯", layout="wide")

st.markdown('\n<style>\na[href^="#"] {\n    display: none !important;\n}\n.block-container {\n    padding-top: 1.2rem !important;\n}\nh1, h2, h3 {\n    letter-spacing: -0.02em;\n}\ndiv[data-testid="stRadio"] {\n    margin-top: 0.25rem;\n    margin-bottom: 1.25rem;\n}\n</style>\n', unsafe_allow_html=True)


st.markdown("""
<style>
.block-container {
    padding-top: 1.3rem;
    padding-bottom: 1rem;
}
h1, h2, h3 {
    margin-top: 0.45rem;
    margin-bottom: 0.45rem;
}
div[data-testid="stDataFrame"] {
    margin-bottom: 0.75rem;
}
.small-note {
    color: #666;
    font-size: 0.92rem;
}
.copy-box {
    border: 1px solid #e6e6e6;
    border-radius: 12px;
    padding: 12px 14px;
    background: #fffdf7;
    margin-top: 8px;
    margin-bottom: 12px;
    font-size: 1.05rem;
}
.pick-card {
    border: 1px solid #e6e6e6;
    border-radius: 14px;
    padding: 12px;
    text-align: center;
    background: #ffffff;
    margin-bottom: 8px;
}
.pick-no {
    font-size: 32px;
    font-weight: 850;
    letter-spacing: 2px;
}
</style>
""", unsafe_allow_html=True)


st.markdown(
    """
    <div class="rap-hero">
        <div class="rap-brand-mark">R</div>
        <div>
            <div class="rap-title">Rumah A Predictor</div>
            <div class="rap-subtitle">Number Pattern Analysis Engine</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

main_menu = "Home"  # Top menu removed for cleaner UI



if main_menu == "Analysis":
    st.subheader("📊 Analysis")
    st.caption("Analisis teknikal diletakkan di sini supaya Home lebih kemas.")

    try:
        ana_c1, ana_c2 = st.columns(2)
        with ana_c1:
            hot_window_analysis = st.selectbox("Hot Digit Window", [10, 30, 50, 100], index=1, key="analysis_hot_window")
            hot_df_analysis = hot_digit_analysis(st.session_state.history, window=hot_window_analysis)
            st.write(f"Hot Digits - {hot_window_analysis} draw terakhir")
            st.dataframe(hot_df_analysis, hide_index=True, use_container_width=True)

        with ana_c2:
            cold_window_analysis = st.selectbox("Cold Digit Window", [10, 30, 50, 100], index=3, key="analysis_cold_window")
            cold_df_analysis = cold_digit_analysis(st.session_state.history, window=cold_window_analysis)
            st.write(f"Cold Digits - {cold_window_analysis} draw terakhir")
            st.dataframe(cold_df_analysis, hide_index=True, use_container_width=True)

        st.info("Hybrid ranking, Score Breakdown dan audit penuh masih boleh dilihat selepas Generate di bahagian Advanced Audit.")
    except Exception:
        st.warning("Analisis belum dapat dipaparkan.")

    st.stop()

if main_menu == "History":
    st.subheader("📜 History")
    st.caption("Paparan 10 draw terakhir daripada data aplikasi.")
    try:
        hist_view = history.copy()
        hist_view["draw_no"] = hist_view["draw_no"].astype(str).str.zfill(6)
        hist_view["draw_date"] = hist_view["draw_date"].astype(str)
        hist_view["first"] = hist_view["first"].astype(str).str.zfill(4)
        hist_view["second"] = hist_view["second"].astype(str).str.zfill(4)
        hist_view["third"] = hist_view["third"].astype(str).str.zfill(4)
        hist_view = hist_view.sort_values("draw_no", ascending=False).head(10)
        hist_view = hist_view.rename(columns={
            "draw_no": "Draw No",
            "draw_date": "Draw Date",
            "first": "1st",
            "second": "2nd",
            "third": "3rd"
        })
        st.dataframe(hist_view[["Draw No", "Draw Date", "1st", "2nd", "3rd"]], hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning("History belum dapat dipaparkan.")
    st.stop()

if main_menu == "Settings":
    st.subheader("⚙️ Settings")
    st.info("Versi ini menggunakan tetapan ringkas untuk APK WebView. Tetapan lanjutan boleh ditambah selepas APK pertama berjaya.")
    st.write("**App Name:** Rumah A Predictor")
    st.write("**Mode:** APK Preparation")
    st.write("**Data Source:** TotoHistoryAll.xlsx")
    st.write("**Auto-save GitHub:** Ikut status Streamlit Secrets")
    st.stop()

if main_menu == "About":
    st.subheader("ℹ️ About")
    st.markdown("""
**Rumah A Predictor** ialah aplikasi paparan analisis dan pemilihan nombor berasaskan data sejarah.

Fokus semasa:
- Paparan mudah untuk telefon
- Bridge V1 dan Bridge V2
- Bridge Pair Shortlist
- Bridge Dua Pair
- Carta 3D V2
- Backtest Bridge
- Sedia untuk dibungkus sebagai Android WebView APK

Nota: Aplikasi ini hanyalah alat analisis data dan tidak menjamin sebarang keputusan.
""")
    st.stop()




st.markdown("""
<style>
/* V20 mobile-ready UI */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem;
}
div[data-testid="stDataFrame"] {
    font-size: 0.92rem;
}
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.7rem;
        padding-right: 0.7rem;
    }
    h1 {
        font-size: 2rem !important;
    }
    h2, h3 {
        font-size: 1.35rem !important;
    }
    div[data-testid="stDataFrame"] {
        font-size: 0.82rem;
    }
    button[kind="secondary"] {
        width: 100%;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* V31.37 — Clean Analysis Dashboard */
:root {
    --rap-ink: #172033;
    --rap-muted: #687386;
    --rap-line: #E2E7F0;
    --rap-surface: #FFFFFF;
    --rap-blue: #3157E5;
    --rap-violet: #7656D8;
    --rap-amber: #D98B18;
    --rap-teal: #0F9488;
}
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 86% 0%, rgba(49,87,229,.07), transparent 25rem),
        #F6F8FC;
}
.block-container {
    max-width: 1180px;
    padding-top: 1.55rem !important;
    padding-bottom: 4rem !important;
}
.rap-hero {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 2px 17px;
    border-bottom: 1px solid var(--rap-line);
    margin-bottom: 15px;
}
.rap-brand-mark {
    width: 46px;
    height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    color: white;
    font-size: 22px;
    font-weight: 850;
    background: linear-gradient(145deg, #3157E5, #6A50D8);
    box-shadow: 0 9px 22px rgba(49,87,229,.22);
}
.rap-title {
    color: var(--rap-ink);
    font-size: 25px;
    line-height: 1.1;
    font-weight: 820;
    letter-spacing: -.035em;
}
.rap-subtitle {
    color: var(--rap-muted);
    font-size: 13px;
    margin-top: 5px;
    letter-spacing: .025em;
}
.rap-status-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 3px 0 22px;
}
.rap-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 11px;
    border-radius: 999px;
    color: #4A5568;
    background: rgba(255,255,255,.9);
    border: 1px solid var(--rap-line);
    font-size: 12px;
    font-weight: 700;
}
.rap-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #22A06B;
    box-shadow: 0 0 0 3px rgba(34,160,107,.12);
}
.rap-section-kicker {
    color: #8490A3;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin: 23px 0 8px;
}
.rap-panel-title {
    color: var(--rap-ink);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -.025em;
    margin: 2px 0 3px;
}
.engine-head {
    display: flex;
    align-items: center;
    gap: 11px;
    margin: 27px 0 7px;
    padding: 12px 15px;
    border-radius: 13px;
    border: 1px solid var(--rap-line);
    background: rgba(255,255,255,.9);
    font-size: 19px;
    font-weight: 800;
    letter-spacing: -.02em;
}
.engine-head::before {
    content: "";
    width: 5px;
    height: 25px;
    border-radius: 99px;
    background: var(--engine-color);
}
.engine-v1 { --engine-color: var(--rap-blue); }
.engine-v2 { --engine-color: var(--rap-violet); }
.engine-pair { --engine-color: var(--rap-amber); }
.engine-board { --engine-color: #3478a4; }
.engine-support { --engine-color: #D06C73; }
.engine-chart { --engine-color: var(--rap-teal); }
.engine-signal { --engine-color: #0B8F77; }
div[data-testid="stMetric"] {
    background: rgba(255,255,255,.94);
    border: 1px solid var(--rap-line);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 0 7px 22px rgba(31,45,74,.045);
}
[data-testid="stMetricLabel"] {
    color: var(--rap-muted);
    font-weight: 700;
}
[data-testid="stMetricValue"] {
    color: var(--rap-ink);
    font-weight: 800;
    letter-spacing: .02em;
}
[data-testid="stForm"] {
    background: rgba(255,255,255,.96);
    border: 1px solid var(--rap-line);
    border-radius: 16px;
    padding: 18px 20px 20px;
    box-shadow: 0 10px 28px rgba(31,45,74,.055);
}
[data-testid="stFormSubmitButton"] button {
    width: 100%;
    min-height: 44px;
    border-radius: 11px;
    border: 0;
    font-weight: 800;
    color: #FFFFFF !important;
    background: linear-gradient(100deg, #0F9F83, #087A73);
    box-shadow: 0 8px 19px rgba(8,122,115,.24);
}
[data-testid="stFormSubmitButton"] button p {
    color: #FFFFFF !important;
}
[data-testid="stFormSubmitButton"] button:hover {
    color: #FFFFFF !important;
    background: linear-gradient(100deg, #0B8F77, #066B66);
    box-shadow: 0 10px 23px rgba(8,122,115,.3);
}
[data-testid="stExpander"] {
    background: rgba(255,255,255,.9);
    border: 1px solid var(--rap-line);
    border-radius: 13px;
    box-shadow: 0 4px 15px rgba(31,45,74,.025);
    overflow: hidden;
}
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}
button[kind="secondary"], button[kind="primary"] {
    border-radius: 10px !important;
    font-weight: 750 !important;
}
hr {
    border-color: var(--rap-line) !important;
}
@media (max-width: 768px) {
    .block-container {
        padding-left: .8rem !important;
        padding-right: .8rem !important;
    }
    .rap-title { font-size: 21px; }
    .rap-brand-mark { width: 42px; height: 42px; }
    .engine-head { font-size: 17px; }
}
</style>
""", unsafe_allow_html=True)

DATA_FILE = Path("TotoHistoryAll.xlsx")
GITHUB_OWNER = "wazley-hub"
GITHUB_REPO = "rumah-a-predictor-v9"
GITHUB_BRANCH = "main"
GITHUB_FILE_PATH = "TotoHistoryAll.xlsx"

def pad4(x):
    try:
        if pd.isna(x):
            return "0000"
    except Exception:
        pass
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(4)[-4:]

def get_pairs(nums):
    pairs = []
    for n in nums:
        pairs.extend([n[0:2], n[1:3], n[2:4]])
    return pairs

def max_repeat(n):
    return max(Counter(n).values())

def score_add(d, num, score, allow_triple_digits=None):
    if len(num) != 4:
        return
    allow_triple_digits = set(allow_triple_digits or [])
    mr = max_repeat(num)

    if mr <= 2:
        d[num] += score
        return

    # V31: triple terkawal.
    # Triple hanya dibenarkan jika digit yang berulang memang kuat dalam latest full result/top3 support.
    if mr == 3:
        counts = Counter(num)
        triple_digit = None
        for digit, cnt in counts.items():
            if cnt == 3:
                triple_digit = digit
                break
        if triple_digit in allow_triple_digits:
            d[num] += score * 0.82

def add_perm4(d, a, b, c, e, score, allow_triple_digits=None):
    combos = [
        (a,b,c,e,1.00), (a,b,e,c,0.96), (a,c,b,e,0.93),
        (a,c,e,b,0.90), (b,a,c,e,0.88), (c,a,b,e,0.86),
        (e,c,b,a,0.82),
    ]
    for x1,x2,x3,x4,m in combos:
        score_add(d, x1+x2+x3+x4, score*m, allow_triple_digits=allow_triple_digits)

@st.cache_data
def load_base_history():
    df = pd.read_excel(DATA_FILE)
    df = df.rename(columns={
        "DrawNo": "draw_no",
        "DrawDate": "draw_date",
        "1stPrizeNo": "first",
        "2ndPrizeNo": "second",
        "3rdPrizeNo": "third",
    })
    df = df[["draw_no", "draw_date", "first", "second", "third"]].dropna()
    # Pastikan semua kolum jadi teks supaya update rekod tidak gagal kerana dtype integer
    for c in ["draw_no", "draw_date", "first", "second", "third"]:
        df[c] = df[c].astype(str).str.strip()
    df["draw_no"] = df["draw_no"].str.zfill(6)
    for c in ["first", "second", "third"]:
        df[c] = df[c].apply(pad4)

    # Susun semula mengikut Draw No supaya latest betul dan tidak bergantung pada susunan baris/cached data.
    df["_draw_sort"] = pd.to_numeric(df["draw_no"], errors="coerce")
    df = df.sort_values("_draw_sort", ascending=True).drop(columns=["_draw_sort"]).reset_index(drop=True)
    return df

def to_original_excel(df):
    out = df.copy()
    out = out.rename(columns={
        "draw_no": "DrawNo",
        "draw_date": "DrawDate",
        "first": "1stPrizeNo",
        "second": "2ndPrizeNo",
        "third": "3rdPrizeNo",
    })
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="Sheet1")
    bio.seek(0)
    return bio


def get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return ""

def github_headers():
    token = get_github_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def update_github_excel(df):
    token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN belum diset dalam Streamlit Secrets."

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    r = requests.get(url, headers=github_headers(), params={"ref": GITHUB_BRANCH}, timeout=30)
    if r.status_code != 200:
        return False, f"Gagal baca fail GitHub. Status {r.status_code}: {r.text[:300]}"

    sha = r.json().get("sha")
    excel_bytes = to_original_excel(df).getvalue()
    encoded = base64.b64encode(excel_bytes).decode("utf-8")
    payload = {
        "message": "Update TotoHistoryAll.xlsx from Streamlit V11",
        "content": encoded,
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }
    r2 = requests.put(url, headers=github_headers(), json=payload, timeout=60)
    if r2.status_code not in (200, 201):
        return False, f"Gagal update GitHub. Status {r2.status_code}: {r2.text[:500]}"
    return True, "GitHub berjaya dikemaskini."


def get_latest_github_excel_bytes():
    token = get_github_token()
    if not token:
        return None, "GITHUB_TOKEN belum diset dalam Streamlit Secrets."

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    r = requests.get(url, headers=github_headers(), params={"ref": GITHUB_BRANCH}, timeout=30)
    if r.status_code != 200:
        return None, f"Gagal baca fail GitHub. Status {r.status_code}: {r.text[:300]}"

    content = r.json().get("content", "")
    if not content:
        return None, "Fail GitHub tiada content."
    try:
        return base64.b64decode(content), "OK"
    except Exception as e:
        return None, f"Gagal decode fail GitHub: {e}"


def normalize_history_dataframe(df):
    """
    Normalize Excel history dataframe supaya format sama seperti load_base_history().
    """
    df = df.rename(columns={
        "DrawNo": "draw_no",
        "DrawDate": "draw_date",
        "1stPrizeNo": "first",
        "2ndPrizeNo": "second",
        "3rdPrizeNo": "third",
    })
    df = df[["draw_no", "draw_date", "first", "second", "third"]].dropna()

    for c in ["draw_no", "draw_date", "first", "second", "third"]:
        df[c] = df[c].astype(str).str.strip()

    df["draw_no"] = df["draw_no"].str.zfill(6)
    for c in ["first", "second", "third"]:
        df[c] = df[c].apply(pad4)

    df["_draw_sort"] = pd.to_numeric(df["draw_no"], errors="coerce")
    df = df.sort_values("_draw_sort", ascending=True).drop(columns=["_draw_sort"]).reset_index(drop=True)
    return df


@st.cache_data(ttl=60)
def load_active_history():
    """
    Load active history.
    Priority:
    1. GitHub TotoHistoryAll.xlsx
    2. Local TotoHistoryAll.xlsx
    """
    latest_bytes, latest_msg = get_latest_github_excel_bytes()
    if latest_bytes:
        try:
            df = pd.read_excel(BytesIO(latest_bytes))
            return normalize_history_dataframe(df), "GitHub"
        except Exception:
            pass

    return load_base_history().copy(), "Local"



@st.cache_data
@st.cache_data(show_spinner=False)
def build_audit(history):
    top3 = history[["first", "second", "third"]].values.tolist()
    firsts = history["first"].tolist()
    recent30, recent100, recent500, all_digit = Counter(), Counter(), Counter(), Counter()
    for nums in top3:
        all_digit.update("".join(nums))
    for nums in top3[-30:]:
        recent30.update("".join(nums))
    for nums in top3[-100:]:
        recent100.update("".join(nums))
    for nums in top3[-500:]:
        recent500.update("".join(nums))

    pair_occ, pair_inh = Counter(), Counter()
    pos_trans = {(pos, cur): Counter() for pos in range(4) for cur in "0123456789"}
    missing_next = Counter()

    for i in range(len(top3)-1):
        cur, nxt = top3[i], top3[i+1]
        cur_pairs, nxt_pairs = set(get_pairs(cur)), set(get_pairs(nxt))
        for p in cur_pairs:
            pair_occ[p] += 1
            if p in nxt_pairs:
                pair_inh[p] += 1

        cur_first, nxt_first = firsts[i], firsts[i+1]
        for pos in range(4):
            pos_trans[(pos, cur_first[pos])][nxt_first[pos]] += 1

        cur_digits, nxt_digits = set("".join(cur)), set("".join(nxt))
        for d in "0123456789":
            if d not in cur_digits and d in nxt_digits:
                missing_next[d] += 1

    pair_rate = {}
    for i in range(100):
        p = f"{i:02d}"
        pair_rate[p] = pair_inh[p] / pair_occ[p] if pair_occ[p] else 0

    return {
        "recent30": recent30, "recent100": recent100, "recent500": recent500,
        "all_digit": all_digit, "pair_rate": pair_rate, "pos_trans": pos_trans,
        "missing_next": missing_next,
    }


@st.cache_data(show_spinner=False)
def build_audit_snapshots_fast_v31_29(history, wanted_indices):
    """Satu pass sejarah untuk semua snapshot backtest; setara dengan build_audit(prefix)."""
    h = history.copy().reset_index(drop=True)
    wanted = {int(x) for x in wanted_indices}
    top3 = [[pad4(r[c]) for c in ("first", "second", "third")] for _, r in h.iterrows()]
    firsts = [nums[0] for nums in top3]
    row_digits = [Counter("".join(nums)) for nums in top3]
    all_digit, recent30, recent100, recent500 = Counter(), Counter(), Counter(), Counter()
    pair_occ, pair_inh, missing_next = Counter(), Counter(), Counter()
    pos_trans = {(pos, cur): Counter() for pos in range(4) for cur in "0123456789"}
    out = {}
    for idx, nums in enumerate(top3):
        dc = row_digits[idx]
        all_digit.update(dc); recent30.update(dc); recent100.update(dc); recent500.update(dc)
        if idx >= 30: recent30.subtract(row_digits[idx - 30]); recent30 += Counter()
        if idx >= 100: recent100.subtract(row_digits[idx - 100]); recent100 += Counter()
        if idx >= 500: recent500.subtract(row_digits[idx - 500]); recent500 += Counter()
        if idx > 0:
            cur, nxt = top3[idx - 1], nums
            cur_pairs, nxt_pairs = set(get_pairs(cur)), set(get_pairs(nxt))
            for p in cur_pairs:
                pair_occ[p] += 1
                if p in nxt_pairs: pair_inh[p] += 1
            for pos in range(4):
                pos_trans[(pos, firsts[idx - 1][pos])][firsts[idx][pos]] += 1
            cur_digits, nxt_digits = set("".join(cur)), set("".join(nxt))
            for d in "0123456789":
                if d not in cur_digits and d in nxt_digits: missing_next[d] += 1
        if idx in wanted:
            pair_rate = {
                f"{i:02d}": (pair_inh[f"{i:02d}"] / pair_occ[f"{i:02d}"] if pair_occ[f"{i:02d}"] else 0)
                for i in range(100)
            }
            out[idx] = {
                "recent30": recent30.copy(), "recent100": recent100.copy(),
                "recent500": recent500.copy(), "all_digit": all_digit.copy(),
                "pair_rate": pair_rate,
                "pos_trans": {k: v.copy() for k, v in pos_trans.items()},
                "missing_next": missing_next.copy(),
            }
    return out














































@st.cache_data(show_spinner=False)





































@st.cache_data(show_spinner=False)



def reset_audit_cache():
    build_audit.clear()

def reset_all_caches():
    build_audit.clear()
    load_base_history.clear()
    try:
        load_active_history.clear()
    except Exception:
        pass

base_history_now, history_source_now = load_active_history()

# Force sync: pastikan session_state ikut source aktif terbaru.
# Keutamaan: GitHub TotoHistoryAll.xlsx. Jika GitHub gagal, fallback local.
if (
    "history" not in st.session_state
    or len(st.session_state.history) != len(base_history_now)
    or str(st.session_state.history.iloc[-1]["draw_no"]).zfill(6) != str(base_history_now.iloc[-1]["draw_no"]).zfill(6)
):
    st.session_state.history = base_history_now.copy()

if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []

history = st.session_state.history
last = history.iloc[-1]

token_status = "Aktif" if get_github_token() else "Belum diset"
history_source_label = history_source_now if "history_source_now" in globals() else "Unknown"
status_dot = '<span class="rap-dot"></span>' if token_status == "Aktif" else ""
st.markdown(
    f"""
    <div class="rap-status-row">
        <span class="rap-badge">{status_dot} GitHub Sync: {token_status}</span>
        <span class="rap-badge">Data: Draw {str(last["draw_no"])}</span>
        <span class="rap-badge">Sumber: {history_source_label}</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# V14: History Manager Lengkap
# -----------------------------

st.markdown('<div class="rap-panel-title">Keputusan Terbaru</div>', unsafe_allow_html=True)
try:
    latest = st.session_state.history.iloc[-1]
    latest_draw = str(latest["draw_no"])
    latest_date = str(latest["draw_date"])
    latest_first = pad4(latest["first"])
    latest_second = pad4(latest["second"])
    latest_third = pad4(latest["third"])

    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.metric("Draw No", latest_draw)
    lc2.metric("1st Prize", latest_first)
    lc3.metric("2nd Prize", latest_second)
    lc4.metric("3rd Prize", latest_third)
    st.caption(f"Tarikh keputusan: {latest_date}")
except Exception:
    st.warning("Keputusan terbaru belum dapat dipaparkan.")

st.markdown('<div class="rap-section-kicker">Tools & Data</div>', unsafe_allow_html=True)
with st.expander("📚 History Manager / Update Keputusan", expanded=False):
    st.subheader("History Manager")
    st.caption("Semua urusan sejarah keputusan dibuat di sini: cari, tambah/update, edit/padam dan download.")

    st.info("Panduan ringkas: gunakan bahagian Tambah / update untuk keputusan baru atau pembetulan. Gunakan Edit / padam hanya jika mahu ubah atau buang draw lama.")


    search_draw = st.text_input("Cari Draw No", value="", placeholder="Contoh: 614826")
    view_df = st.session_state.history.copy()

    view_df["draw_no"] = view_df["draw_no"].astype(str).str.zfill(6)

    if search_draw.strip():
        keyword = search_draw.strip().zfill(6)
        view_df = view_df[view_df["draw_no"] == keyword]
        st.caption(f"Keputusan carian untuk Draw No: {keyword}")
    else:
        view_df = view_df.sort_values("draw_no", ascending=False).head(10)
        st.caption("Paparan 10 draw terakhir")

    recent_view = view_df.copy().rename(columns={
        "draw_no": "Draw No",
        "draw_date": "Draw Date",
        "first": "1st",
        "second": "2nd",
        "third": "3rd",
    })
    st.dataframe(recent_view, hide_index=True, use_container_width=True)

    download_col1, download_col2 = st.columns(2)
    with download_col1:
        st.download_button(
            "Download Current App History",
            data=to_original_excel(st.session_state.history),
            file_name="TotoHistoryAll_current_app.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_current_history",
        )

    with download_col2:
        latest_bytes, latest_msg = get_latest_github_excel_bytes()
        if latest_bytes:
            pass  # Duplicate GitHub history download button removed
        else:
            st.info("Latest GitHub History belum boleh dimuat turun. Pastikan token aktif.")

    with st.expander("History Manager: Edit / padam draw", expanded=False):
        draw_options = st.session_state.history["draw_no"].astype(str).tolist()
        default_idx = len(draw_options) - 1 if draw_options else 0

        if search_draw.strip() and not view_df.empty:
            search_options = view_df["draw_no"].astype(str).tolist()
            selected_draw = st.selectbox(
                "Pilih Draw No untuk edit/padam",
                options=search_options,
                index=len(search_options)-1,
                key="edit_draw_select_search",
            )
        else:
            selected_draw = st.selectbox(
                "Pilih Draw No untuk edit/padam",
                options=draw_options,
                index=default_idx,
                key="edit_draw_select",
            )

        selected_rows = st.session_state.history[
            st.session_state.history["draw_no"].astype(str) == str(selected_draw)
        ]

        if not selected_rows.empty:
            selected_row = selected_rows.iloc[-1]

            action = st.radio(
                "Tindakan",
                ["Update rekod", "Padam rekod"],
                horizontal=True,
                key="history_action_radio",
            )

            if action == "Update rekod":
                with st.form("edit_existing_draw_form"):
                    c0, c1, c2, c3, c4 = st.columns(5)
                    edit_draw_no = c0.text_input("Draw No", value=str(selected_row["draw_no"]), key="edit_draw_no")
                    edit_date = c1.text_input("Draw Date", value=str(selected_row["draw_date"]), key="edit_draw_date")
                    edit_first = c2.text_input("1st", value=pad4(selected_row["first"]), max_chars=4, key="edit_first")
                    edit_second = c3.text_input("2nd", value=pad4(selected_row["second"]), max_chars=4, key="edit_second")
                    edit_third = c4.text_input("3rd", value=pad4(selected_row["third"]), max_chars=4, key="edit_third")
                    edit_auto_save = st.checkbox("Auto-save ke GitHub", value=True, key="edit_auto_save")
                    edit_clicked = st.form_submit_button("Update draw dipilih")

                if edit_clicked:
                    if not (edit_first and edit_second and edit_third):
                        st.error("Sila isi 1st, 2nd dan 3rd.")
                    else:
                        new_history = st.session_state.history.copy()
                        for col in ["draw_no", "draw_date", "first", "second", "third"]:
                            new_history[col] = new_history[col].astype(str)

                        match_idx = new_history.index[
                            new_history["draw_no"].astype(str) == str(selected_draw)
                        ].tolist()

                        if not match_idx:
                            st.error("Draw tidak dijumpai dalam history.")
                        else:
                            idx = match_idx[-1]
                            new_history.at[idx, "draw_no"] = str(edit_draw_no).strip()
                            new_history.at[idx, "draw_date"] = str(edit_date).strip()
                            new_history.at[idx, "first"] = pad4(edit_first)
                            new_history.at[idx, "second"] = pad4(edit_second)
                            new_history.at[idx, "third"] = pad4(edit_third)

                            st.session_state.history = new_history
                            build_audit.clear()

                            if edit_auto_save:
                                ok, msg = update_github_excel(new_history)
                                if ok:
                                    st.success(f"Draw {selected_draw} berjaya dikemaskini dan GitHub berjaya dikemaskini.")
                                    reset_all_caches()
                                else:
                                    st.warning(f"Draw {selected_draw} dikemaskini dalam sesi app, tetapi GitHub belum dikemaskini.")
                                    st.error(msg)
                            else:
                                st.success(f"Draw {selected_draw} dikemaskini dalam sesi app sahaja.")

                            st.rerun()

            else:
                st.warning(f"Anda akan memadam Draw No {selected_draw}. Tindakan ini tidak boleh dibatalkan selepas auto-save.")
                confirm_delete = st.checkbox("Saya sahkan mahu padam rekod ini", key="confirm_delete")
                delete_auto_save = st.checkbox("Auto-save ke GitHub", value=True, key="delete_auto_save")
                if st.button("Padam draw dipilih", disabled=not confirm_delete):
                    new_history = st.session_state.history.copy()
                    for col in ["draw_no", "draw_date", "first", "second", "third"]:
                        new_history[col] = new_history[col].astype(str)

                    match_idx = new_history.index[
                        new_history["draw_no"].astype(str) == str(selected_draw)
                    ].tolist()

                    if not match_idx:
                        st.error("Draw tidak dijumpai dalam history.")
                    else:
                        idx = match_idx[-1]
                        new_history = new_history.drop(index=idx).reset_index(drop=True)

                        st.session_state.history = new_history
                        build_audit.clear()

                        if delete_auto_save:
                            ok, msg = update_github_excel(new_history)
                            if ok:
                                st.success(f"Draw {selected_draw} berjaya dipadam dan GitHub berjaya dikemaskini.")
                                reset_all_caches()
                            else:
                                st.warning(f"Draw {selected_draw} dipadam dalam sesi app, tetapi GitHub belum dikemaskini.")
                                st.error(msg)
                        else:
                            st.success(f"Draw {selected_draw} dipadam dalam sesi app sahaja.")

                        st.rerun()

    st.divider()

    st.divider()


if False:
    pass
# Analysis / Hot & Cold Digits removed
    st.subheader("V17 Analysis")
    ana_c1, ana_c2 = st.columns(2)
    with ana_c1:
        hot_window = st.selectbox("Hot Digit Window", [10, 30, 50, 100], index=1)
        hot_df_preview = hot_digit_analysis(st.session_state.history, window=hot_window)
        st.write(f"Hot Digits - {hot_window} draw terakhir")
        st.dataframe(hot_df_preview, hide_index=True, use_container_width=True)
    with ana_c2:
        cold_window = st.selectbox("Cold Digit Window", [10, 30, 50, 100], index=3)
        cold_df_preview = cold_digit_analysis(st.session_state.history, window=cold_window)
        st.write(f"Cold Digits - {cold_window} draw terakhir")
        st.dataframe(cold_df_preview, hide_index=True, use_container_width=True)

    st.divider()

    with st.expander("History Manager: Tambah / update keputusan", expanded=True):
        with st.form("add_result_form"):
            c0, c1, c2, c3, c4 = st.columns(5)
            try:
                suggested_draw = str(int(last["draw_no"]) + 100)
            except Exception:
                suggested_draw = ""
            next_draw = c0.text_input("Draw No", value=suggested_draw)
            draw_date = c1.text_input("Draw Date", value="")
            new_first = c2.text_input("1st", max_chars=4)
            new_second = c3.text_input("2nd", max_chars=4)
            new_third = c4.text_input("3rd", max_chars=4)

            draw_exists = str(next_draw).strip() in set(st.session_state.history["draw_no"].astype(str))
            if draw_exists:
                st.warning(f"Draw No {next_draw} sudah wujud dalam history. Pilih sama ada mahu update rekod lama atau tambah baris baru.")
                save_mode = st.radio(
                    "Tindakan",
                    ["Update rekod sedia ada", "Tambah sebagai baris baru"],
                    horizontal=True,
                )
            else:
                save_mode = "Tambah sebagai baris baru"

            auto_save = st.checkbox("Auto-save ke GitHub", value=True)
            add_clicked = st.form_submit_button("Simpan keputusan")

        if add_clicked:
            if not (new_first and new_second and new_third):
                st.error("Sila isi 1st, 2nd dan 3rd.")
            else:
                new_row = {
                    "draw_no": str(next_draw).strip(),
                    "draw_date": str(draw_date).strip(),
                    "first": pad4(new_first),
                    "second": pad4(new_second),
                    "third": pad4(new_third),
                }

                new_history = st.session_state.history.copy()
                # Tukar semua kolum kepada object/string supaya pandas tidak reject update nilai teks
                for col in ["draw_no", "draw_date", "first", "second", "third"]:
                    new_history[col] = new_history[col].astype(str)
                match_idx = new_history.index[new_history["draw_no"].astype(str) == str(next_draw).strip()].tolist()

                if match_idx and save_mode == "Update rekod sedia ada":
                    idx = match_idx[-1]
                    # Update satu kolum demi satu kolum supaya stabil di Streamlit Cloud / pandas baru
                    new_history.at[idx, "draw_no"] = str(new_row["draw_no"])
                    new_history.at[idx, "draw_date"] = str(new_row["draw_date"])
                    new_history.at[idx, "first"] = str(new_row["first"])
                    new_history.at[idx, "second"] = str(new_row["second"])
                    new_history.at[idx, "third"] = str(new_row["third"])
                    action_msg = f"Draw {next_draw} dikemaskini."
                else:
                    new_history = pd.concat([new_history, pd.DataFrame([new_row])], ignore_index=True)
                    action_msg = f"Draw {next_draw} ditambah sebagai baris baru."

                st.session_state.history = new_history
                reset_audit_cache()

                if auto_save:
                    ok, msg = update_github_excel(new_history)
                    if ok:
                        st.success(action_msg + " GitHub berjaya dikemaskini.")
                        reset_all_caches()
                    else:
                        st.warning(action_msg + " Tetapi GitHub belum dikemaskini.")
                        st.error(msg)
                else:
                    st.success(action_msg + " Disimpan dalam sesi app sahaja.")
                st.rerun()

    st.download_button(
        "Download Updated TotoHistoryAll.xlsx",
        data=to_original_excel(st.session_state.history),
        file_name="TotoHistoryAll_updated.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    last = st.session_state.history.iloc[-1]




def unordered_digit_key4(n):
    """Kunci semakan hit tanpa susunan; tidak digunakan untuk memilih calon."""
    try:
        return "".join(sorted(pad4(n)))
    except Exception:
        return ""


def pair_digit_key(pair):
    """Samakan pair terbalik, contohnya 13 dan 31."""
    return "".join(sorted(str(pair).zfill(2)[-2:]))


def keep_first_pair_orientation(pair_rows):
    """Kekalkan orientasi pair yang muncul dahulu sahaja."""
    kept = []
    seen = set()
    for row in pair_rows:
        key = pair_digit_key(row.get("Pair", ""))
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept








def build_bridge_model_v31_9(first, second, third):
    import pandas as pd
    nums=[pad4(first),pad4(second),pad4(third)]
    existing_digits=sorted(set("".join(nums)))
    missing_digits=sorted(set("0123456789")-set(existing_digits))
    pair_rows=[]; base_pairs=[]
    number_meta={}
    bridge_order=[]

    for label,no in zip(["1st","2nd","3rd"],nums):
        for ptype,pair in zip(["Front","Middle","Back"],[no[:2],no[1:3],no[2:4]]):
            base_pairs.append(pair)
            pair_rows.append({"Source":label,"No":no,"Pair Type":ptype,"Pair":pair})

    pair_rows = keep_first_pair_orientation(pair_rows)
    base_pairs = [row["Pair"] for row in pair_rows]

    for row in pair_rows:
        pair=row["Pair"]
        src=row["Source"]
        ptype=row["Pair Type"]
        for md in missing_digits:
            for ed in existing_digits:
                # V31.21: ikut tertib pair asal.
                # Contoh 82 + 7 + 6 = 8276, bukan canonical 2678 untuk paparan.
                display_no = f"{pair}{md}{ed}"
                if len(display_no)==4 and display_no.isdigit():
                    if display_no not in number_meta:
                        number_meta[display_no]={
                            "Display No":display_no,
                            "Formula List":[],
                            "Base Pairs":set(),
                            "Sources":set(),
                            "Pair Types":set(),
                            "Missing Digits":set(),
                            "Existing Digits":set(),
                        }
                        bridge_order.append(display_no)

                    formula=f"{pair}+{md}+{ed}"
                    number_meta[display_no]["Formula List"].append(formula)
                    number_meta[display_no]["Base Pairs"].add(pair)
                    number_meta[display_no]["Sources"].add(src)
                    number_meta[display_no]["Pair Types"].add(ptype)
                    number_meta[display_no]["Missing Digits"].add(md)
                    number_meta[display_no]["Existing Digits"].add(ed)

    rows=[]
    for order_idx, display_no in enumerate(bridge_order, start=1):
        meta = number_meta[display_no]
        rows.append({
            "No": meta["Display No"],
            "Order": order_idx,
            "Formula Support": len(set(meta["Formula List"])),
            "Source Support": len(meta["Sources"]),
            "Position Support": len(meta["Pair Types"]),
            "Base Pair Support": len(meta["Base Pairs"]),
            "Base Pairs": " / ".join(sorted(meta["Base Pairs"])),
            "Sources": " / ".join(sorted(meta["Sources"])),
            "Pair Types": " / ".join(sorted(meta["Pair Types"])),
            "Missing Digits": " / ".join(sorted(meta["Missing Digits"])),
            "Existing Digits": " / ".join(sorted(meta["Existing Digits"])),
            "Formula List": " / ".join(sorted(set(meta["Formula List"]))),
        })

    bridge_df=pd.DataFrame(rows)
    if not bridge_df.empty:
        bridge_df=bridge_df.sort_values(["Order"]).reset_index(drop=True)

    text="🧪 Rumah A Predictor - Bridge Model\n\n"
    text+="Base Pairs:\n"+" / ".join(base_pairs)
    text+="\n\nMissing Digits:\n"+" / ".join(missing_digits)
    text+="\n\nExisting Digits:\n"+" / ".join(existing_digits)
    nums_out=bridge_df["No"].astype(str).tolist() if not bridge_df.empty and "No" in bridge_df.columns else []
    text+=f"\n\nBridge Numbers (Total: {len(nums_out)}):\n"
    text += "\n".join([" / ".join(nums_out[i:i+10]) for i in range(0,len(nums_out),10)]) if nums_out else "Tiada output."
    return pd.DataFrame(pair_rows), bridge_df, text


def build_bridge_engine_v2_pair_double_digit(first, second, third):
    """Bridge V2: pair + 2 missing digits OR pair + 2 existing digits."""
    nums = [pad4(first), pad4(second), pad4(third)]
    existing_digits = sorted(set("".join(nums)))
    missing_digits = sorted(set("0123456789") - set(existing_digits))
    pair_rows, base_pairs = [], []
    for label, no in zip(["1st", "2nd", "3rd"], nums):
        for pair_type, pair in zip(["Front", "Middle", "Back"], [no[:2], no[1:3], no[2:4]]):
            pair_rows.append({"Source": label, "No": no, "Pair Type": pair_type, "Pair": pair})
            base_pairs.append(pair)
    pair_rows = keep_first_pair_orientation(pair_rows)
    base_pairs = [row["Pair"] for row in pair_rows]

    number_meta = {}
    def add_candidate(pair, d1, d2, mode, source, pair_type):
        display_no = f"{pair}{d1}{d2}"
        meta = number_meta.setdefault(display_no, {
            "No": display_no, "Modes": set(), "Base Pairs": set(),
            "Sources": set(), "Pair Types": set(), "Formula List": set(),
        })
        meta["Modes"].add(mode); meta["Base Pairs"].add(pair)
        meta["Sources"].add(source); meta["Pair Types"].add(pair_type)
        meta["Formula List"].add(f"{pair}+{d1}{d2}")

    for row in pair_rows:
        pair, source, pair_type = row["Pair"], row["Source"], row["Pair Type"]
        for digit_pool, mode in [(missing_digits, "2 Missing"), (existing_digits, "2 Existing")]:
            for d1 in digit_pool:
                for d2 in digit_pool:
                    if d1 != d2:
                        add_candidate(pair, d1, d2, mode, source, pair_type)

    rows = []
    for order, meta in enumerate(number_meta.values(), 1):
        rows.append({
            "No": meta["No"], "Order": order,
            "Mode": " / ".join(sorted(meta["Modes"])),
            "Formula Support": len(meta["Formula List"]), "Source Support": len(meta["Sources"]),
            "Position Support": len(meta["Pair Types"]), "Base Pair Support": len(meta["Base Pairs"]),
            "Base Pairs": " / ".join(sorted(meta["Base Pairs"])),
            "Sources": " / ".join(sorted(meta["Sources"])),
            "Pair Types": " / ".join(sorted(meta["Pair Types"])),
            "Formula List": " / ".join(sorted(meta["Formula List"])),
        })
    bridge_v2_df = pd.DataFrame(rows)
    text = "🧪 Rumah A Predictor - Bridge Engine V2\n\n"
    text += "Base Pairs:\n" + " / ".join(base_pairs)
    text += "\n\nMissing Digits:\n" + " / ".join(missing_digits)
    text += "\n\nExisting Digits:\n" + " / ".join(existing_digits)
    for mode in ("2 Missing", "2 Existing"):
        vals = bridge_v2_df[bridge_v2_df["Mode"].str.contains(mode, regex=False)]["No"].astype(str).tolist() if not bridge_v2_df.empty else []
        text += f"\n\n{mode} Numbers (Total: {len(vals)}):\n"
        text += "\n".join(" / ".join(vals[i:i+10]) for i in range(0, len(vals), 10)) if vals else "Tiada output."
    return pd.DataFrame(pair_rows), bridge_v2_df, text


def _ordered_top3_pairs(first, second, third):
    """Pair Top 3 unik; pasangan terbalik dikira sebagai pair yang sama."""
    rows = []
    for source, no in zip(("1st", "2nd", "3rd"), (pad4(first), pad4(second), pad4(third))):
        for pair_type, pair in zip(("Front", "Middle", "Back"), (no[:2], no[1:3], no[2:4])):
            rows.append({"Source": source, "Pair Type": pair_type, "Pair": pair})
    return keep_first_pair_orientation(rows)


@st.cache_data(show_spinner=False)
def build_bridge_pair_priority(history, first, second, third, lookback=500):
    """Rank pair daripada draw terkini; satu draw dikira sekali jika V1 atau V2 hit."""
    columns = [
        "Priority", "Source", "Pair Position", "Current Pair",
        "V1 Hit", "V2 Hit", "Total Support", "Hit Rate %", "Transitions",
    ]
    if history is None or history.empty or len(history) < 2:
        return pd.DataFrame(columns=columns)

    h = history.copy().reset_index(drop=True)
    if lookback and len(h) > int(lookback) + 1:
        h = h.tail(int(lookback) + 1).reset_index(drop=True)
    slots = [
        ("1st", "Front", 0, "first"),
        ("1st", "Middle", 1, "first"),
        ("1st", "Back", 2, "first"),
        ("2nd", "Front", 0, "second"),
        ("2nd", "Middle", 1, "second"),
        ("2nd", "Back", 2, "second"),
        ("3rd", "Front", 0, "third"),
        ("3rd", "Middle", 1, "third"),
        ("3rd", "Back", 2, "third"),
    ]
    v1_hits = Counter()
    v2_hits = Counter()
    combined_hits = Counter()
    transitions = len(h) - 1
    for idx in range(len(h) - 1):
        source_numbers = [pad4(h.iloc[idx][c]) for c in ("first", "second", "third")]
        existing_digits = sorted(set("".join(source_numbers)))
        missing_digits = sorted(set("0123456789") - set(existing_digits))
        target_digit_keys = {
            unordered_digit_key4(h.iloc[idx + 1][c]) for c in ("first", "second", "third")
        }
        for source, position, start, column in slots:
            pair = pad4(h.iloc[idx][column])[start:start + 2]
            bridge_v1_digit_keys = {
                unordered_digit_key4(f"{pair}{missing}{existing}")
                for missing in missing_digits
                for existing in existing_digits
            }
            bridge_v2_digit_keys = {
                unordered_digit_key4(f"{pair}{d1}{d2}")
                for pool in (missing_digits, existing_digits)
                for d1 in pool
                for d2 in pool
                if d1 != d2
            }
            v1_hit_now = bool(bridge_v1_digit_keys & target_digit_keys)
            v2_hit_now = bool(bridge_v2_digit_keys & target_digit_keys)
            if v1_hit_now:
                v1_hits[(source, position)] += 1
            if v2_hit_now:
                v2_hits[(source, position)] += 1
            if v1_hit_now or v2_hit_now:
                combined_hits[(source, position)] += 1

    current = {"first": pad4(first), "second": pad4(second), "third": pad4(third)}
    rows = []
    for original_order, (source, position, start, column) in enumerate(slots):
        v1_hit = int(v1_hits[(source, position)])
        v2_hit = int(v2_hits[(source, position)])
        combined_hit = int(combined_hits[(source, position)])
        rows.append({
            "Source": source,
            "Pair Position": position,
            "Current Pair": current[column][start:start + 2],
            "V1 Hit": v1_hit,
            "V2 Hit": v2_hit,
            "Total Support": combined_hit,
            "Hit Rate %": round((combined_hit / transitions) * 100, 1) if transitions else 0.0,
            "Transitions": transitions,
            "_Original Order": original_order,
        })

    ranked = pd.DataFrame(rows).sort_values(
        ["Total Support", "V1 Hit", "_Original Order"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    kept_indexes, seen_pair_keys = [], set()
    for index, row in ranked.iterrows():
        key = pair_digit_key(row["Current Pair"])
        if key in seen_pair_keys:
            continue
        seen_pair_keys.add(key)
        kept_indexes.append(index)
    ranked = ranked.loc[kept_indexes].reset_index(drop=True)
    ranked.insert(0, "Priority", range(1, len(ranked) + 1))
    return ranked.drop(columns=["_Original Order"])


def build_bridge_pair_priority_numbers(pair, pair_audit_row, first, second, third):
    """Keluarkan V1 dan V2 untuk satu pair sahaja; provenance route tidak dicampurkan."""
    columns = ["Pair", "No", "Route"]
    if not pair:
        return pd.DataFrame(columns=columns), ""

    nums = [pad4(first), pad4(second), pad4(third)]
    existing_digits = sorted(set("".join(nums)))
    missing_digits = sorted(set("0123456789") - set(existing_digits))
    pair = str(pair).zfill(2)[-2:]
    number_meta = {}

    def add_number(no, route):
        key = (route, no)
        if key not in number_meta:
            number_meta[key] = {"Pair": pair, "No": no, "Route": route}

    for missing in missing_digits:
        for existing in existing_digits:
            add_number(f"{pair}{missing}{existing}", "Bridge V1")
    for d1 in missing_digits:
        for d2 in missing_digits:
            if d1 != d2:
                add_number(f"{pair}{d1}{d2}", "Bridge V2 - 2 Missing")
    for d1 in existing_digits:
        for d2 in existing_digits:
            if d1 != d2:
                add_number(f"{pair}{d1}{d2}", "Bridge V2 - 2 Existing")

    rows = [
        {
            "Pair": meta["Pair"], "No": meta["No"], "Route": meta["Route"],
        }
        for meta in number_meta.values()
    ]
    number_df = pd.DataFrame(rows, columns=columns)
    text_lines = [
        "🧭 Rumah A Predictor - Bridge Pair Shortlist", "",
        f'Pair Pilihan: {pair}',
        f'Sumber Ranking: {pair_audit_row["Source"]} Prize - {pair_audit_row["Pair Position"]}',
        f'V1 Hit: {int(pair_audit_row["V1 Hit"])}',
        f'V2 Hit: {int(pair_audit_row["V2 Hit"])}',
        f'Total Support: {int(pair_audit_row["Total Support"])}',
    ]
    for route in ("Bridge V1", "Bridge V2 - 2 Missing", "Bridge V2 - 2 Existing"):
        route_values = number_df[number_df["Route"].str.contains(route, regex=False)]["No"].tolist()
        text_lines.extend(["", f"{route} (Pilihan Unik: {len(route_values)}):"])
        text_lines.extend(" / ".join(route_values[i:i + 10]) for i in range(0, len(route_values), 10))
    text_lines.extend(["", f"Jumlah Pilihan Unik Pair {pair}: {len(number_df)}"])
    return number_df, "\n".join(text_lines)






def build_second_pair_shortlist(pair, pair_numbers_df, first, second, third):
    """Tapis nombor asal yang mengekalkan generator pair dan current pair lain."""
    columns = ["Generator Pair", "No", "Bridge", "Pair Kedua"]
    if pair_numbers_df is None or pair_numbers_df.empty:
        return pd.DataFrame(columns=columns), ""

    current_rows = _ordered_top3_pairs(first, second, third)
    current_pairs = list(dict.fromkeys(str(row["Pair"]) for row in current_rows))
    other_pairs = [value for value in current_pairs if value != str(pair)]
    rows = []
    for _, row in pair_numbers_df.iterrows():
        number = pad4(row["No"])
        supporting_pairs = [value for value in other_pairs if value in number]
        if not supporting_pairs:
            continue
        rows.append({
            "Generator Pair": str(pair),
            "No": number,
            "Bridge": str(row["Route"]),
            "Pair Kedua": " / ".join(supporting_pairs),
        })

    shortlist_df = pd.DataFrame(rows, columns=columns)
    text_lines = [
        "🔗 Rumah A Predictor - Bridge Dua Pair", "",
        f"Generator Pair: {pair}",
        f"Jumlah Pilihan: {len(shortlist_df)}",
    ]
    for route in ("Bridge V1", "Bridge V2 - 2 Missing", "Bridge V2 - 2 Existing"):
        route_df = shortlist_df[shortlist_df["Bridge"] == route]
        if route_df.empty:
            continue
        text_lines.extend(["", f"{route} ({len(route_df)} Pilihan):"])
        for _, item in route_df.iterrows():
            text_lines.append(
                f'{item["No"]} | Pair Kedua {item["Pair Kedua"]}'
            )
    return shortlist_df, "\n".join(text_lines)






def build_chart_3d_signal_v31_39(first, second, third, bridge_v1_df=None, bridge_v2_df=None):
    """Carta ringan: Menegak/L + Bridge sahaja, tanpa imbasan bentuk Tetris 4D."""
    numbers = [pad4(first), pad4(second), pad4(third)]
    digit_sums = [sum(int(digit) for digit in number) for number in numbers]
    digit_roots = [0 if value == 0 else 1 + (value - 1) % 9 for value in digit_sums]
    total_sum = str(sum(digit_sums))
    root_sum = str(sum(digit_roots))
    cross_rows = [
        "".join(str(int(top_digit) + int(bottom_digit)) for bottom_digit in root_sum)
        for top_digit in total_sum
    ]
    final_row = str(sum(int(digit) for digit in total_sum)) + str(
        sum(int(digit) for digit in root_sum)
    )
    derived_rows = cross_rows + [final_row]
    chart_rows = [total_sum, root_sum] + derived_rows

    three_d_rows, seen = [], set()
    max_width = max(len(row) for row in derived_rows)
    for column in range(max_width):
        if all(column < len(row) for row in derived_rows):
            anchor = "".join(row[column] for row in derived_rows)
            key = ("Menegak", anchor)
            if len(anchor) == 3 and key not in seen:
                seen.add(key)
                three_d_rows.append({"Pilihan": "Menegak", "3D": anchor})
    for row_index in range(len(derived_rows) - 1):
        top_row, bottom_row = derived_rows[row_index], derived_rows[row_index + 1]
        for column in range(min(len(top_row), len(bottom_row)) - 1):
            choices = [
                ("L Kiri", top_row[column] + bottom_row[column] + bottom_row[column + 1]),
                ("L Kanan", top_row[column + 1] + bottom_row[column + 1] + bottom_row[column]),
            ]
            # Lengkapkan orientasi L atas pada baris campur-silang sahaja.
            # Blok 13 / 12 menghasilkan 113; baris jumlah akhir tidak diperluas.
            if row_index < len(cross_rows) - 1:
                upper_l = top_row[column] + bottom_row[column] + top_row[column + 1]
                if (
                    upper_l not in {anchor for _, anchor in choices}
                    and not any(existing_anchor == upper_l for _, existing_anchor in seen)
                ):
                    choices.append(("L Atas", upper_l))
            for label, anchor in choices:
                if any(
                    existing_label != "Menegak" and existing_anchor == anchor
                    for existing_label, existing_anchor in seen
                ):
                    continue
                key = (label, anchor)
                if key not in seen:
                    seen.add(key)
                    three_d_rows.append({"Pilihan": label, "3D": anchor})
    three_d_df = pd.DataFrame(three_d_rows, columns=["Pilihan", "3D"])

    def bridge_lookup(frame):
        numbers = []
        if frame is None or frame.empty:
            return numbers
        for _, row in frame.iterrows():
            number = pad4(row.get("No", ""))
            if number and number not in numbers:
                numbers.append(number)
        return numbers

    v1_numbers = bridge_lookup(bridge_v1_df)
    v2_numbers = bridge_lookup(bridge_v2_df)
    confirmed_rows = []
    for _, choice in three_d_df.iterrows():
        anchor = str(choice["3D"])
        for bridge_name, bridge_numbers in (
            ("V1", v1_numbers),
            ("V2", v2_numbers),
        ):
            for number in bridge_numbers:
                if Counter(anchor) - Counter(number):
                    continue
                confirmed_rows.append({
                    "Pilihan": str(choice["Pilihan"]),
                    "3D": anchor,
                    "No": number,
                    "Bridge": bridge_name,
                })
    confirmed_df = pd.DataFrame(
        confirmed_rows,
        columns=["Pilihan", "3D", "No", "Bridge"],
    )
    if not confirmed_df.empty:
        confirmed_df = (
            confirmed_df.drop_duplicates()
            .sort_values(["Pilihan", "3D", "Bridge", "No"])
            .reset_index(drop=True)
        )

    vertical_values = three_d_df[three_d_df["Pilihan"] == "Menegak"]["3D"].tolist()
    l_values = three_d_df[three_d_df["Pilihan"] != "Menegak"]["3D"].tolist()
    chart_text = (
        "🧩 Rumah A Predictor - Carta 3D V2\n\n"
        f"Top 3: {' / '.join(numbers)}\n"
        f"Jumlah Digit: {' / '.join(str(value) for value in digit_sums)}\n"
        f"Digital Root: {' / '.join(str(value) for value in digit_roots)}\n"
        f"Asas: {total_sum} / {root_sum}\n\n"
        + "\n".join(chart_rows)
        + f"\n\nPilihan Menegak: {' / '.join(vertical_values) or 'Tiada'}"
        + f"\nPilihan L: {' / '.join(l_values) or 'Tiada'}"
    )
    choice_lines = [
        "🎯 Rumah A Predictor - Pilihan Carta 3D + Bridge",
        "",
        f"Pilihan Menegak: {' / '.join(vertical_values) or 'Tiada'}",
        f"Pilihan L: {' / '.join(l_values) or 'Tiada'}",
        f"Jumlah 3D Carta + Bridge: {len(confirmed_df)}",
    ]
    if confirmed_df.empty:
        choice_lines.extend(["", "Tiada pilihan Carta 3D yang disahkan Bridge."])
    else:
        choice_lines.extend(["", "3D Carta + Bridge:"])
        for _, row in confirmed_df.iterrows():
            choice_lines.append(
                f'{row["Pilihan"]} {row["3D"]} | {row["Bridge"]} | {row["No"]}'
            )
    meta = {
        "Rows": chart_rows,
        "3D Choices": three_d_df,
        "3D Confirmed": confirmed_df,
    }
    return chart_text, "\n".join(choice_lines), meta


@st.cache_data(show_spinner=False)
def load_latest_full_result_for_chart():
    """Baca satu draw keputusan penuh terkini untuk pengesahan Carta 3D."""
    path = Path("TotoFullResult.xlsx")
    if not path.exists():
        return {}
    frame = pd.read_excel(path)
    if frame.empty:
        return {}
    if "DrawNo" in frame.columns:
        frame["_draw_sort"] = pd.to_numeric(frame["DrawNo"], errors="coerce")
        latest = frame.sort_values("_draw_sort").iloc[-1]
    else:
        latest = frame.iloc[-1]

    def collect(prefix):
        columns = [
            column for column in frame.columns
            if str(column).startswith(prefix)
        ]
        columns.sort(
            key=lambda column: int("".join(filter(str.isdigit, str(column))) or 0)
        )
        rows = []
        for column in columns:
            value = latest.get(column, "")
            if pd.isna(value):
                continue
            rows.append({
                "Position": str(column).replace(prefix, ""),
                "No": pad4(value),
            })
        return rows

    return {
        "DrawNo": str(latest.get("DrawNo", "")).replace(".0", ""),
        "Top3": [
            pad4(latest.get("1stPrizeNo", "")),
            pad4(latest.get("2ndPrizeNo", "")),
            pad4(latest.get("3rdPrizeNo", "")),
        ],
        "Special": collect("SpecialNo"),
        "Consolation": collect("ConsolationNo"),
    }


def build_chart_full_result_confirmation(chart_3d_df, first, second, third):
    """Tapis pilihan Carta 3D menggunakan Special/Consolation draw yang sama."""
    columns = ["3D", "Pengesahan", "No Sumber", "Kedudukan", "Pilihan Carta"]
    latest = load_latest_full_result_for_chart()
    if not latest or chart_3d_df is None or chart_3d_df.empty:
        return pd.DataFrame(columns=columns), {}, ""

    current_top3 = [pad4(first), pad4(second), pad4(third)]
    if latest.get("Top3") != current_top3:
        return pd.DataFrame(columns=columns), {
            "stale": True,
            "DrawNo": latest.get("DrawNo", ""),
        }, ""

    rows = []
    for _, choice in chart_3d_df.iterrows():
        anchor = str(choice.get("3D", "")).strip()
        if len(anchor) != 3:
            continue
        anchor_counter = Counter(anchor)
        for source_name in ("Special", "Consolation"):
            for source in latest.get(source_name, []):
                if anchor_counter - Counter(source["No"]):
                    continue
                rows.append({
                    "3D": anchor,
                    "Pengesahan": source_name,
                    "No Sumber": source["No"],
                    "Kedudukan": source["Position"],
                    "Pilihan Carta": str(choice.get("Pilihan", "")),
                })
    detail = pd.DataFrame(rows, columns=columns).drop_duplicates()
    special = []
    consolation = []
    if not detail.empty:
        special = list(dict.fromkeys(
            detail.loc[detail["Pengesahan"] == "Special", "3D"].astype(str)
        ))
        consolation = list(dict.fromkeys(
            detail.loc[detail["Pengesahan"] == "Consolation", "3D"].astype(str)
        ))
    both = [anchor for anchor in special if anchor in set(consolation)]
    meta = {
        "stale": False,
        "DrawNo": latest.get("DrawNo", ""),
        "Special": special,
        "Consolation": consolation,
        "Both": both,
    }
    copy_text = "\n".join([
        "🔎 Rumah A Predictor - Carta 3D Disahkan Result Penuh",
        "",
        f"Draw Sumber: {meta['DrawNo']}",
        f"Disahkan Special: {' / '.join(special) or 'Tiada'}",
        f"Disahkan Consolation: {' / '.join(consolation) or 'Tiada'}",
        f"Disahkan Kedua-duanya: {' / '.join(both) or 'Tiada'}",
    ])
    return detail, meta, copy_text






@st.cache_data(show_spinner=False)
def run_backtest_bridge_dde_lite_v31_24_5(history_df, test_draws=30):
    import json
    import time
    t0 = time.perf_counter()
    if history_df is None or history_df.empty or len(history_df) < 2:
        return pd.DataFrame(), pd.DataFrame()
    h = history_df.copy().reset_index(drop=True)
    for col in ("first", "second", "third"):
        h[col] = h[col].apply(pad4)
    latest_idx = len(h) - 1
    count = max(1, min(int(test_draws), latest_idx + 1))
    start_idx = max(0, latest_idx - count + 1)
    cache_path = Path(".backtest_row_cache_v31_45_unique_pairs.json")
    cache = {}
    try:
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("version") == "v31.45-unique-pairs":
                cache = payload.get("rows", {})
    except Exception:
        cache = {}
    rows = []
    for idx in range(start_idx, latest_idx + 1):
        source = h.iloc[idx]
        first, second, third = (pad4(source[c]) for c in ("first", "second", "third"))
        if idx + 1 < len(h):
            nxt = h.iloc[idx + 1]
            next_sig = "|".join([str(nxt.get("draw_no", ""))] + [pad4(nxt[c]) for c in ("first", "second", "third")])
        else:
            nxt, next_sig = None, "PENDING"
        key = "|".join([str(source.get("draw_no", idx)), first, second, third, next_sig])
        if key in cache:
            rows.append(cache[key])
            continue
        _, v1_df, _ = build_bridge_model_v31_9(first, second, third)
        _, v2_df, _ = build_bridge_engine_v2_pair_double_digit(first, second, third)
        v1_list = v1_df["No"].astype(str).tolist() if not v1_df.empty else []
        v2_list = v2_df["No"].astype(str).tolist() if not v2_df.empty else []
        v1_digit_keys = {unordered_digit_key4(x) for x in v1_list}
        v2_digit_keys = {unordered_digit_key4(x) for x in v2_list}
        v2_missing = {
            unordered_digit_key4(x)
            for x in v2_df[v2_df["Mode"].str.contains("2 Missing", regex=False)]["No"].astype(str)
        } if not v2_df.empty else set()
        v2_existing = {
            unordered_digit_key4(x)
            for x in v2_df[v2_df["Mode"].str.contains("2 Existing", regex=False)]["No"].astype(str)
        } if not v2_df.empty else set()
        if nxt is None:
            next_draw, next_result = "", "Belum ada next draw"
            actual_nums, actual_digit_keys = [], []
            status = "PENDING"
        else:
            actual_nums = [pad4(nxt[c]) for c in ("first", "second", "third")]
            actual_digit_keys = [unordered_digit_key4(x) for x in actual_nums]
            next_draw, next_result, status = str(nxt.get("draw_no", "")), " / ".join(actual_nums), "DONE"
        v1_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v1_digit_keys]
        v2_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_digit_keys]
        missing_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_missing]
        existing_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_existing]
        union_hits = list(dict.fromkeys(v1_hits + v2_hits))
        def hit_state(values):
            return "PENDING" if status == "PENDING" else ("YES" if values else "NO")
        row = {
            "Source Draw": str(source.get("draw_no", idx)),
            "Source Result": f"{first} / {second} / {third}",
            "Next Draw": next_draw, "Next Result": next_result,
            "Bridge Count": len(v1_list), "Bridge List": " / ".join(v1_list),
            "Bridge Hit": hit_state(v1_hits), "Bridge Hit Number": " / ".join(v1_hits),
            "Bridge V2 Count": len(v2_list), "Bridge V2 List": " / ".join(v2_list),
            "Bridge V2 Hit": hit_state(v2_hits), "Bridge V2 Hit Number": " / ".join(v2_hits),
            "Bridge V2 2-Missing Hit": hit_state(missing_hits),
            "Bridge V2 2-Missing Hit Number": " / ".join(missing_hits),
            "Bridge V2 2-Existing Hit": hit_state(existing_hits),
            "Bridge V2 2-Existing Hit Number": " / ".join(existing_hits),
            "Hit": hit_state(union_hits), "Hit Number": " / ".join(union_hits),
        }
        rows.append(row)
        cache[key] = row
    try:
        cache_path.write_text(json.dumps({"version": "v31.45-unique-pairs", "rows": cache}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    detail = pd.DataFrame(rows)
    valid = detail[detail.get("Hit", pd.Series(dtype=str)).astype(str).isin(["YES", "NO"])]
    total = len(valid)
    v1_yes = int(valid.get("Bridge Hit", pd.Series(dtype=str)).eq("YES").sum())
    v2_yes = int(valid.get("Bridge V2 Hit", pd.Series(dtype=str)).eq("YES").sum())
    union_yes = int(valid.get("Hit", pd.Series(dtype=str)).eq("YES").sum())
    miss_yes = int(valid.get("Bridge V2 2-Missing Hit", pd.Series(dtype=str)).eq("YES").sum())
    exist_yes = int(valid.get("Bridge V2 2-Existing Hit", pd.Series(dtype=str)).eq("YES").sum())
    summary = pd.DataFrame([
        {"Metric": "Tested source draws", "Value": total},
        {"Metric": "Pending latest draw", "Value": int(detail.get("Hit", pd.Series(dtype=str)).eq("PENDING").sum())},
        {"Metric": "Bridge V1 YES", "Value": v1_yes},
        {"Metric": "Bridge V1 Hit Rate %", "Value": round(v1_yes / total * 100, 1) if total else 0},
        {"Metric": "Bridge V2 YES", "Value": v2_yes},
        {"Metric": "Bridge V2 Hit Rate %", "Value": round(v2_yes / total * 100, 1) if total else 0},
        {"Metric": "V2 2-Missing YES", "Value": miss_yes},
        {"Metric": "V2 2-Existing YES", "Value": exist_yes},
        {"Metric": "Bridge V1 atau V2 Hit", "Value": union_yes},
        {"Metric": "Total Unique Hit Rate %", "Value": round(union_yes / total * 100, 1) if total else 0},
        {"Metric": "Elapsed Seconds", "Value": round(time.perf_counter() - t0, 3)},
    ])
    return summary, detail

def _first_existing_backtest_column(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def build_clean_backtest_quick_review(detail_df):
    """Paparan ringkas keputusan draw serta hit Bridge V1 dan V2."""
    q = pd.DataFrame(index=detail_df.index)
    for target, choices in {
        "Source Draw": ["Source Draw"],
        "Source Result": ["Source Result"],
        "Next Draw": ["Next Draw"],
        "Next Result": ["Next Result"],
        "Bridge Hit No": ["Bridge Hit Number", "Bridge Hit No"],
        "Bridge V2 Hit No": ["Bridge V2 Hit Number", "Bridge V2 Hit No"],
    }.items():
        source = _first_existing_backtest_column(detail_df, choices)
        q[target] = detail_df[source].fillna("").astype(str) if source else ""
    return q.reset_index(drop=True)


def build_clean_backtest_summary(detail_df):
    """Summary mesra pengguna untuk Bridge V1 dan V2."""
    hit_status = detail_df.get("Hit", pd.Series("", index=detail_df.index)).astype(str)
    valid_mask = hit_status.isin(["YES", "NO"])
    pending_mask = hit_status.eq("PENDING")
    valid = detail_df.loc[valid_mask].copy()
    total_draws = len(detail_df)
    completed = len(valid)
    pending = int(pending_mask.sum())

    bridge_hits = 0
    if "Bridge Hit" in valid.columns:
        bridge_hits = int(valid["Bridge Hit"].astype(str).eq("YES").sum())
    else:
        bridge_col = _first_existing_backtest_column(valid, ["Bridge Hit Number", "Bridge Hit No"])
        if bridge_col:
            bridge_hits = int(valid[bridge_col].fillna("").astype(str).str.strip().ne("").sum())

    bridge_v2_hits = int(valid.get("Bridge V2 Hit", pd.Series("", index=valid.index)).astype(str).eq("YES").sum())
    bridge_union_hits = int((
        valid.get("Bridge Hit", pd.Series("", index=valid.index)).astype(str).eq("YES")
        | valid.get("Bridge V2 Hit", pd.Series("", index=valid.index)).astype(str).eq("YES")
    ).sum())
    rows = [
        {"Metric": "Jumlah Draw", "Value": total_draws},
        {"Metric": "Draw Selesai", "Value": completed},
        {"Metric": "Draw Pending", "Value": pending},
        {"Metric": "Bridge Hit", "Value": bridge_hits},
        {"Metric": "Bridge Hit Rate %", "Value": round((bridge_hits / completed) * 100, 1) if completed else 0},
        {"Metric": "Bridge V2 Hit", "Value": bridge_v2_hits},
        {"Metric": "Bridge V2 Hit Rate %", "Value": round((bridge_v2_hits / completed) * 100, 1) if completed else 0},
        {"Metric": "Bridge V1 atau V2 Hit", "Value": bridge_union_hits},
        {"Metric": "Total Unique Hit Rate %", "Value": round((bridge_union_hits / completed) * 100, 1) if completed else 0},
    ]
    summary = pd.DataFrame(rows)
    summary["Value"] = summary["Value"].astype(str)
    return summary


def simple_backtest_excel_bytes(summary_df, detail_df):
    from io import BytesIO
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    quick_df = build_clean_backtest_quick_review(detail_df)
    clean_summary_df = build_clean_backtest_summary(detail_df)

    # Enjin lama tidak lagi dipaparkan dalam Detail fail muat turun.
    obsolete_prefixes = ("Bridge V2 Selection", "Bridge V2 Top", "Bridge V3", "BDE ")
    clean_detail_df = detail_df.drop(
        columns=[c for c in detail_df.columns if str(c).startswith(obsolete_prefixes)],
        errors="ignore",
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        quick_df.to_excel(writer, sheet_name="Quick Review", index=False)
        clean_summary_df.to_excel(writer, sheet_name="Summary", index=False)
        clean_detail_df.to_excel(writer, sheet_name="Detail", index=False)

        wb = writer.book
        navy = "17365D"
        pale_green = "EAF7EE"
        pale_blue = "EEF4FF"
        light_border = Side(style="thin", color="E5E7EB")

        quick_ws = wb["Quick Review"]
        quick_ws.freeze_panes = "A2"
        quick_ws.sheet_view.showGridLines = False
        quick_ws.auto_filter.ref = quick_ws.dimensions
        for cell in quick_ws[1]:
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
        quick_ws.row_dimensions[1].height = 26
        for row in quick_ws.iter_rows(min_row=2, max_row=quick_ws.max_row):
            for cell in row:
                cell.border = Border(bottom=light_border)
                cell.alignment = Alignment(vertical="center")
                cell.number_format = "@"
            for cell in row[4:6]:
                cell.fill = PatternFill("solid", fgColor=pale_green)
                cell.font = Font(color="166534", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
        for col, width in {"A": 14, "B": 26, "C": 14, "D": 26, "E": 18, "F": 20}.items():
            quick_ws.column_dimensions[col].width = width

        summary_ws = wb["Summary"]
        summary_ws.sheet_view.showGridLines = False
        summary_ws.freeze_panes = "A2"
        summary_ws.auto_filter.ref = summary_ws.dimensions
        for cell in summary_ws[1]:
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row_no in range(2, summary_ws.max_row + 1):
            summary_ws.cell(row_no, 1).border = Border(bottom=light_border)
            summary_ws.cell(row_no, 2).border = Border(bottom=light_border)
            summary_ws.cell(row_no, 2).font = Font(color=navy, bold=True)
            summary_ws.cell(row_no, 2).alignment = Alignment(horizontal="center")
            if row_no in (5, 6):
                fill = pale_green
            elif row_no in (7, 8):
                fill = pale_blue
            else:
                fill = "F8FAFC"
            summary_ws.cell(row_no, 1).fill = PatternFill("solid", fgColor=fill)
            summary_ws.cell(row_no, 2).fill = PatternFill("solid", fgColor=fill)
        summary_ws.column_dimensions["A"].width = 26
        summary_ws.column_dimensions["B"].width = 18

        detail_ws = wb["Detail"]
        detail_ws.freeze_panes = "A2"
        detail_ws.auto_filter.ref = detail_ws.dimensions
        for cell in detail_ws[1]:
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")

    output.seek(0)
    return output.getvalue()

# -----------------------------
# V31.6: Simple Backtest
# -----------------------------
st.markdown('<div class="rap-section-kicker">Backtest</div>', unsafe_allow_html=True)
with st.expander("🧪 Backtest Bridge V1 + V2", expanded=False):
    st.caption("Fast Backtest: keputusan draw lama dibaca daripada cache; hanya draw baharu atau berubah dikira semula.")
    bt_col1, bt_col2 = st.columns(2)
    with bt_col1:
        bt_draws = st.selectbox("Jumlah source draw untuk test", [10, 20, 30, 50, 100, 200, 300, 500], index=2, key="simple_bt_draws_v31_6")
    with bt_col2:
        st.write("")
        st.write("")
        run_bt = st.button("Run Backtest Turbo Lite", key="run_backtest_turbo_v31_7")

    if run_bt:
        with st.spinner("Backtest Bridge V1 + V2 sedang berjalan..."):
            bt_summary, bt_detail = run_backtest_bridge_dde_lite_v31_24_5(
                st.session_state.history, test_draws=bt_draws
            )

        if bt_detail.empty:
            st.warning("Backtest tidak menghasilkan data.")
        else:
            clean_bt_summary = build_clean_backtest_summary(bt_detail)
            st.subheader("Summary Bridge V1 + V2")
            st.dataframe(clean_bt_summary, hide_index=True, use_container_width=True)

            st.subheader("Detail")
            st.dataframe(bt_detail, hide_index=True, use_container_width=True)

            bt_bytes = simple_backtest_excel_bytes(bt_summary, bt_detail)
            st.download_button(
                "Download Backtest Turbo Excel",
                data=bt_bytes,
                file_name="Rumah_A_Predictor_Backtest_Clean_Review_V31_23_3.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_backtest_turbo_v31_7"
            )


with st.form("predict_form"):
    st.markdown('<div class="rap-panel-title">Generate Analisis</div>', unsafe_allow_html=True)
    st.caption(
        "Keputusan terbaru telah diisi secara automatik. Tekan Generate untuk "
        "analisis Bridge berdasarkan nombor formula asal."
    )
    c1, c2, c3 = st.columns(3)
    first = c1.text_input("1st Prize", value=last["first"], max_chars=4)
    second = c2.text_input("2nd Prize", value=last["second"], max_chars=4)
    third = c3.text_input("3rd Prize", value=last["third"], max_chars=4)
    submitted = st.form_submit_button("Generate")

if submitted:
    st.success("Analisis Bridge berjaya dijana.")

    # -----------------------------
    # Bridge V1
    # -----------------------------
    st.markdown('<div class="engine-head engine-v1">Bridge V1</div>', unsafe_allow_html=True)
    st.caption(
        "Pair depan/tengah/belakang + 1 missing digit + 1 existing digit. "
        "Nombor formula asal dikekalkan."
    )

    bridge_df = pd.DataFrame()
    bridge_pair_df = pd.DataFrame()
    try:
        bridge_pair_df, bridge_df, bridge_text = build_bridge_model_v31_9(first, second, third)
        if bridge_df.empty:
            st.info("Bridge Model belum menghasilkan output.")
        else:
            st.caption(f"Jumlah Pilihan Bridge: {len(bridge_df)}")
            copy_button_clean("📋 Copy Bridge V1", bridge_text, "bridge_model_v31_9")
            with st.expander("Lihat Detail Bridge V1", expanded=False):
                st.markdown("**Base Pair**")
                st.dataframe(bridge_pair_df, hide_index=True, use_container_width=True)
                st.markdown("**Senarai Bridge**")
                st.dataframe(bridge_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Model belum dapat dipaparkan: {e}")

    # -----------------------------
    # Bridge Engine V2 - Pair + 2D Missing / Pair + 2D Existing
    # -----------------------------
    st.markdown('<div class="engine-head engine-v2">Bridge V2</div>', unsafe_allow_html=True)
    st.caption("Base pair + 2 digit missing, atau base pair + 2 digit existing. Digit pasangan mestilah berbeza.")
    bridge_v2_df = pd.DataFrame()
    try:
        bridge_v2_pair_df, bridge_v2_df, bridge_v2_text = build_bridge_engine_v2_pair_double_digit(first, second, third)
        if bridge_v2_df.empty:
            st.info("Bridge V2 belum menghasilkan output.")
        else:
            v2_missing_count = int(bridge_v2_df["Mode"].str.contains("2 Missing", regex=False).sum())
            v2_existing_count = int(bridge_v2_df["Mode"].str.contains("2 Existing", regex=False).sum())
            st.caption(
                f"Jumlah pilihan unik: {len(bridge_v2_df)} | "
                f"2 Missing: {v2_missing_count} | 2 Existing: {v2_existing_count}"
            )
            copy_button_clean("📋 Copy Bridge V2", bridge_v2_text, "bridge_engine_v2_double_digit")
            with st.expander("Lihat Detail Bridge V2", expanded=False):
                st.dataframe(bridge_v2_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Engine V2 belum dapat dipaparkan: {e}")

    # -----------------------------
    # Selection Engine V1
    # -----------------------------
    st.markdown('<div class="engine-head engine-support">Selection Engine</div>', unsafe_allow_html=True)
    try:
        selection = build_selection_engine(
            st.session_state.history, first, second, third, lookback=300
        )
        selection_numbers = selection.get("combined", [])
        double_numbers = selection.get("double", [])
        st.markdown(
            f'**Double Signal:** {" / ".join(double_numbers) or "Tiada"}  \n'
            f'**Top 10:** {" / ".join(selection_numbers) or "Tiada"}'
        )
        selection_text = (
            "ðŸŽ¯ Rumah A Predictor - Selection Engine\n\n"
            f'Double Signal:\n{" / ".join(double_numbers) or "Tiada"}\n\n'
            f'Top 10:\n{" / ".join(selection_numbers) or "Tiada"}'
        )
        copy_button_clean(
            "ðŸ“‹ Copy Selection",
            selection_text,
            "copy_selection_engine_v1",
        )
        with st.expander("Lihat sumber pilihan", expanded=False):
            st.markdown(
                f'**Pair Slot:** {" / ".join(selection.get("pair", [])) or "Tiada"}  \n'
                f'**Carta:** {" / ".join(selection.get("chart", [])) or "Tiada"}'
            )
    except Exception as e:
        st.warning(f"Selection Engine belum dapat dipaparkan: {e}")

    # -----------------------------
    # Bridge Pair Priority - pair carry-forward daripada Top 3
    # -----------------------------
    st.markdown('<div class="engine-head engine-pair">Bridge Pair Shortlist</div>', unsafe_allow_html=True)
    st.caption(
        "Pair disusun berdasarkan satu hit gabungan V1/V2 bagi 500 draw terkini. "
        "Jika V1 dan V2 sama-sama hit dalam satu draw, ia tetap dikira sekali. Buka pair yang dikehendaki; "
        "nombor dan butang Copy bagi pair itu sahaja tersedia di dalamnya."
    )
    try:
        pair_priority_df = build_bridge_pair_priority(
            st.session_state.history, first, second, third
        )
        if pair_priority_df.empty:
            st.info("Data sejarah belum mencukupi untuk Bridge Pair Shortlist.")
        else:
            ranking_text = " / ".join(
                f'#{int(row["Priority"])} {row["Current Pair"]}'
                for _, row in pair_priority_df.iterrows()
            )
            st.markdown(f"**Ranking Pair:** {ranking_text}")

            shown_pairs = set()
            for _, audit_row in pair_priority_df.iterrows():
                pair = str(audit_row["Current Pair"]).zfill(2)[-2:]
                if pair in shown_pairs:
                    continue
                shown_pairs.add(pair)
                pair_numbers_df, pair_copy_text = build_bridge_pair_priority_numbers(
                    pair, audit_row, first, second, third
                )
                sources = pair_priority_df[pair_priority_df["Current Pair"].astype(str).str.zfill(2) == pair]
                source_text = " / ".join(
                    f'{row["Source"]} {row["Pair Position"]}' for _, row in sources.iterrows()
                )
                label = (
                    f'#{int(audit_row["Priority"])} Pair {pair} | '
                    f'Hit {int(audit_row["Total Support"])}/{int(audit_row["Transitions"])}'
                )
                with st.expander(label, expanded=False):
                    st.caption(
                        f'Sumber semasa: {source_text} | '
                        f'Hit Gabungan: {int(audit_row["Total Support"])} '
                        f'({float(audit_row["Hit Rate %"]):.1f}%) | '
                        f'V1 Hit: {int(audit_row["V1 Hit"])} | '
                        f'V2 Hit: {int(audit_row["V2 Hit"])}'
                    )
                    copy_button_clean(
                        f"📋 Copy Pair {pair}",
                        pair_copy_text,
                        f"bridge_pair_shortlist_{pair}_v31_35_5",
                    )
                    v1_rows = pair_numbers_df[pair_numbers_df["Route"] == "Bridge V1"]
                    v2_rows = pair_numbers_df[pair_numbers_df["Route"].str.startswith("Bridge V2")]
                    st.markdown(f"**Bridge V1 — {len(v1_rows)} pilihan unik**")
                    st.dataframe(v1_rows, hide_index=True, use_container_width=True)
                    st.markdown(f"**Bridge V2 — {len(v2_rows)} pilihan unik**")
                    st.dataframe(v2_rows, hide_index=True, use_container_width=True)

            with st.expander("Lihat audit pair 500 draw terkini", expanded=False):
                st.dataframe(pair_priority_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Pair Shortlist belum dapat dipaparkan: {e}")

    # -----------------------------
    # Bridge Dua Pair - blok tambahan, tidak mengubah shortlist asal
    # -----------------------------
    st.markdown('<div class="engine-head engine-support">Bridge Dua Pair</div>', unsafe_allow_html=True)
    st.caption(
        "Pilihan daripada generator pair yang turut mengandungi sekurang-kurangnya "
        "satu pair lain daripada keputusan semasa. Shortlist asal di atas tidak berubah."
    )
    try:
        second_pair_rank_df = build_bridge_pair_priority(
            st.session_state.history, first, second, third
        )
        shown_second_pairs = set()
        for _, audit_row in second_pair_rank_df.iterrows():
            pair = str(audit_row["Current Pair"]).zfill(2)[-2:]
            if pair in shown_second_pairs:
                continue
            shown_second_pairs.add(pair)
            pair_numbers_df, _ = build_bridge_pair_priority_numbers(
                pair, audit_row, first, second, third
            )
            second_pair_df, second_pair_text = build_second_pair_shortlist(
                pair, pair_numbers_df, first, second, third
            )
            with st.expander(
                f'#{int(audit_row["Priority"])} Pair {pair} — {len(second_pair_df)} pilihan dua pair',
                expanded=False,
            ):
                copy_button_clean(
                    f"📋 Copy Pair Kedua {pair}",
                    second_pair_text,
                    f"second_pair_family_{pair}_v31_35_6",
                )
                if second_pair_df.empty:
                    st.info("Tiada pilihan dua pair untuk pair ini.")
                else:
                    st.dataframe(second_pair_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Dua Pair belum dapat dipaparkan: {e}")

    # -----------------------------
    # Carta 3D V2 - Menegak/L sahaja untuk Historical Signal Engine
    # -----------------------------
    st.markdown('<div class="engine-head engine-chart">Carta 3D V2</div>', unsafe_allow_html=True)
    st.caption(
        "Jumlah digit dan campur silang untuk pilihan 3D Menegak/L. "
        "Pilihan ini menjadi input dalaman Historical Signal Engine."
    )
    try:
        chart_v2_text, _, chart_v2_meta = build_chart_3d_signal_v31_39(
            first, second, third, bridge_df, bridge_v2_df
        )
        st.code("\n".join(chart_v2_meta.get("Rows", [])), language=None)
        chart_3d_df = chart_v2_meta.get("3D Choices", pd.DataFrame())
        chart_3d_confirmed_df = chart_v2_meta.get("3D Confirmed", pd.DataFrame())
        vertical_values = chart_3d_df[chart_3d_df["Pilihan"] == "Menegak"]["3D"].tolist() if not chart_3d_df.empty else []
        l_values = chart_3d_df[chart_3d_df["Pilihan"] != "Menegak"]["3D"].tolist() if not chart_3d_df.empty else []
        st.markdown(
            f'**Pilihan Menegak:** {" / ".join(vertical_values) or "Tiada"}  \n'
            f'**Pilihan L:** {" / ".join(l_values) or "Tiada"}  \n'
            f'**Carta 3D + Bridge:** {len(chart_3d_confirmed_df)}'
        )
        copy_button_clean(
            "📋 Copy Carta 3D V2",
            chart_v2_text,
            "copy_chart_3d_v2_v31_39",
        )

        # Keputusan penuh hanya mengesahkan pilihan Carta yang sudah wujud.
        # Output ini tidak memasuki Historical Signal Engine.
        st.markdown(
            '<div class="engine-head engine-support">Carta 3D Disahkan Result Penuh</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Penapis eksperimen: Special dan Consolation draw yang sama hanya "
            "mengesahkan pilihan Carta sedia ada. Ia tidak mencipta nombor baharu."
        )
        confirmation_df, confirmation_meta, confirmation_text = (
            build_chart_full_result_confirmation(
                chart_3d_df, first, second, third
            )
        )
        if confirmation_meta.get("stale"):
            st.info(
                "TotoFullResult belum sepadan dengan keputusan semasa. "
                "Kemas kini fail keputusan penuh untuk menggunakan pengesahan ini."
            )
        elif not confirmation_meta:
            st.info("TotoFullResult belum tersedia untuk pengesahan Carta.")
        else:
            special_values = confirmation_meta.get("Special", [])
            consolation_values = confirmation_meta.get("Consolation", [])
            both_values = confirmation_meta.get("Both", [])
            st.markdown(
                f'**Disahkan Special:** {" / ".join(special_values) or "Tiada"}  \n'
                f'**Disahkan Consolation:** {" / ".join(consolation_values) or "Tiada"}  \n'
                f'**Disahkan kedua-duanya:** {" / ".join(both_values) or "Tiada"}'
            )
            copy_button_clean(
                "📋 Copy Pengesahan Carta 3D",
                confirmation_text,
                "copy_chart_full_result_confirmation_v31_43",
            )
            if not confirmation_df.empty:
                with st.expander("Lihat sumber pengesahan", expanded=False):
                    st.dataframe(
                        confirmation_df,
                        hide_index=True,
                        use_container_width=True,
                    )

    except Exception as e:
        st.warning(f"Carta 3D V2 belum dapat dipaparkan: {e}")
