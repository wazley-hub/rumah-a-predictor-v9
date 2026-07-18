
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


def prediction_stability_index(history, current_first=None, current_second=None, current_third=None, rounds=5, top_n=20):
    """
    PSI: ukur kestabilan nombor dengan simulasi beberapa snapshot history terkini.
    Jika nombor kerap muncul dalam TopN dan rank purata bagus, PSI lebih tinggi.
    """
    rows = []
    tracker = {}

    if len(history) < 30:
        return pd.DataFrame(columns=["No", "Appearances", "Avg Rank", "Frequency Score", "Rank Bonus", "PSI"])

    start_i = max(30, len(history) - rounds + 1)
    snapshots = list(range(start_i, len(history) + 1))

    for snap_end in snapshots:
        hist_snap = history.iloc[:snap_end].copy()
        if hist_snap.empty:
            continue

        latest = hist_snap.iloc[-1]
        try:
            res = generate(hist_snap, latest["first"], latest["second"], latest["third"])
            top_df = res["hybrid_all"].head(top_n)
        except Exception:
            continue

        for _, row in top_df.iterrows():
            no = str(row["No"]).zfill(4)
            rank = int(row["Rank"])
            if no not in tracker:
                tracker[no] = {"ranks": [], "appearances": 0}
            tracker[no]["ranks"].append(rank)
            tracker[no]["appearances"] += 1

    total_rounds = max(1, len(snapshots))

    for no, data in tracker.items():
        appearances = data["appearances"]
        avg_rank = sum(data["ranks"]) / len(data["ranks"]) if data["ranks"] else top_n
        freq_score = (appearances / total_rounds) * 100

        if avg_rank <= 5:
            rank_bonus = 20
        elif avg_rank <= 10:
            rank_bonus = 10
        elif avg_rank <= 20:
            rank_bonus = 5
        else:
            rank_bonus = 0

        psi = min(100, round((freq_score * 0.7) + (rank_bonus * 0.3), 1))

        rows.append({
            "No": no,
            "Appearances": appearances,
            "Avg Rank": round(avg_rank, 2),
            "Frequency Score": round(freq_score, 1),
            "Rank Bonus": rank_bonus,
            "PSI": psi,
        })

    return pd.DataFrame(rows).sort_values(["PSI", "Appearances"], ascending=False).reset_index(drop=True)


def add_stability_to_hybrid(hybrid_df, stability_df):
    df = hybrid_df.copy()
    if stability_df is None or stability_df.empty:
        df["Stability"] = 0
        return df

    psi_map = dict(zip(stability_df["No"].astype(str).str.zfill(4), stability_df["PSI"]))
    df["No"] = df["No"].astype(str).str.zfill(4)
    df["Stability"] = df["No"].map(psi_map).fillna(0).round(1)
    return df


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
        style="border:0;border-radius:10px;background:#2563eb;color:white;padding:10px 16px;font-size:15px;font-weight:800;margin-right:8px;">
            {label}
        </button>
        <span id="msg_{key_name}" style="color:#15803d;font-size:14px;font-weight:700;margin-left:8px;"></span>
        """,
        height=48
    )

st.set_page_config(page_title="Rumah A Predictor", layout="wide")

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


st.markdown("### 🎯 Rumah A Predictor")
st.caption("AI Number Selection Engine")

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

Fokus V25:
- Paparan mudah untuk telefon
- AI Pick Of The Day
- Top 3 Utama
- Strong Buy Tambahan
- Backup Pool
- Final Mobile UI
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

def top_keys(counter_or_dict, n=10):
    return [k for k, v in sorted(counter_or_dict.items(), key=lambda kv: kv[1], reverse=True)[:n]]

def num_stat_score(num, audit_data, missing, present):
    s = 0
    for d in num:
        s += audit_data["recent30"][d] / 25
        s += audit_data["recent100"][d] / 90
        s += audit_data["recent500"][d] / 450
        if d in missing:
            s += 2.2
        if d in present:
            s += 0.6
    if max_repeat(num) == 2:
        s -= 0.4
    return s

def num_position_score(num, audit_data, cur_first):
    """
    V31:
    - Sebelum ini guna 1st prize sahaja.
    - Sekarang boleh terima senarai reference [(no, weight), ...] supaya 1st/2nd/3rd boleh menyokong position score.
    """
    s = 0

    if isinstance(cur_first, (list, tuple)) and cur_first and isinstance(cur_first[0], (list, tuple)):
        refs = [(pad4(n), float(w)) for n, w in cur_first]
    else:
        refs = [(pad4(cur_first), 1.0)]

    weight_total = sum(w for _, w in refs) or 1.0

    for pos, d in enumerate(num):
        for ref_no, w in refs:
            s += (w / weight_total) * (audit_data["pos_trans"][(pos, ref_no[pos])][d] / 45)

    return s

def num_pair_score(num, audit_data, current_pair_score):
    s = 0
    for p in [num[0:2], num[1:3], num[2:4]]:
        if p in current_pair_score:
            s += 8 * current_pair_score[p]
        s += 3 * audit_data["pair_rate"].get(p, 0)
    return s

def make_table(d, n):
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return pd.DataFrame({
        "Rank": range(1, len(items)+1),
        "No": [x[0] for x in items],
        "Score": [round(x[1], 3) for x in items],
    })


def add_confidence(df):
    df = df.copy()
    if df.empty or "Score" not in df.columns:
        df["Confidence"] = []
        return df

    max_score = float(df["Score"].max()) if len(df) else 0
    mean_score = float(df["Score"].mean()) if len(df) else 0

    def calc_conf(score):
        if max_score <= 0:
            return 50.0
        strength = score / max_score
        separation = (score - mean_score) / max_score
        conf = 45 + (strength * 40) + (separation * 20)
        return round(max(35, min(95, conf)), 1)

    df["Confidence"] = df["Score"].apply(calc_conf)
    return df

def hot_digit_analysis(history, window=30):
    recent = history.tail(window)
    prev = history.iloc[max(0, len(history) - (window * 2)): max(0, len(history) - window)]

    recent_counter = Counter()
    prev_counter = Counter()

    for _, row in recent.iterrows():
        recent_counter.update(pad4(row["first"]))
        recent_counter.update(pad4(row["second"]))
        recent_counter.update(pad4(row["third"]))

    for _, row in prev.iterrows():
        prev_counter.update(pad4(row["first"]))
        prev_counter.update(pad4(row["second"]))
        prev_counter.update(pad4(row["third"]))

    rows = []
    for d in "0123456789":
        current = recent_counter[d]
        previous = prev_counter[d]
        diff = current - previous
        trend = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        rows.append({"Digit": d, "Count": current, "Prev Count": previous, "Trend": trend, "Diff": diff})
    return pd.DataFrame(rows).sort_values(["Count", "Diff"], ascending=False).reset_index(drop=True)

def cold_digit_analysis(history, window=100):
    recent = history.tail(window)
    rows = []
    for d in "0123456789":
        gap = 0
        found = False
        for _, row in recent.iloc[::-1].iterrows():
            text = pad4(row["first"]) + pad4(row["second"]) + pad4(row["third"])
            if d in text:
                found = True
                break
            gap += 1

        total_count = 0
        for _, row in recent.iterrows():
            total_count += (pad4(row["first"]) + pad4(row["second"]) + pad4(row["third"])).count(d)

        expected = (len(recent) * 12) / 10 if len(recent) else 0
        underperform = round(expected - total_count, 2)

        rows.append({
            "Digit": d,
            "Window": window,
            "Draws Since Last Seen": gap if found else len(recent),
            "Count": total_count,
            "Expected": round(expected, 2),
            "Underperform": underperform,
        })

    return pd.DataFrame(rows).sort_values(
        ["Draws Since Last Seen", "Underperform"],
        ascending=False
    ).reset_index(drop=True)

def _score_map(df):
    if df is None or df.empty:
        return {}
    return {str(row["No"]).zfill(4): float(row["Score"]) for _, row in df.iterrows()}

def score_breakdown_table(hybrid_df, stat_df, pos_df, pair_df, theory_df):
    """
    V17.1 Fix:
    Papar contribution sebenar apabila nombor wujud dalam sub-model.
    Jika nombor naik kerana hybrid logic/interleave/candidate boost, ia dikira sebagai Hybrid Boost.
    Ini lebih jujur berbanding memaksa semua score masuk ke Stat/Pos/Pair/Theory.
    """
    stat_map = _score_map(stat_df)
    pos_map = _score_map(pos_df)
    pair_map = _score_map(pair_df)
    theory_map = _score_map(theory_df)

    rows = []
    for _, row in hybrid_df.iterrows():
        no = str(row["No"]).zfill(4)
        stat = float(stat_map.get(no, 0))
        pos = float(pos_map.get(no, 0))
        pair = float(pair_map.get(no, 0))
        theory = float(theory_map.get(no, 0))
        direct_total = stat + pos + pair + theory
        hybrid_total = float(row["Score"])
        boost = max(0, hybrid_total - direct_total)

        if hybrid_total > 0:
            stat_pct = round((stat / hybrid_total) * 100, 1)
            pos_pct = round((pos / hybrid_total) * 100, 1)
            pair_pct = round((pair / hybrid_total) * 100, 1)
            theory_pct = round((theory / hybrid_total) * 100, 1)
            boost_pct = round((boost / hybrid_total) * 100, 1)
        else:
            stat_pct = pos_pct = pair_pct = theory_pct = boost_pct = 0

        main_source = max(
            [
                ("Stat", stat),
                ("Position", pos),
                ("Pair", pair),
                ("Theory", theory),
                ("Hybrid Boost", boost),
            ],
            key=lambda x: x[1],
        )[0]

        rows.append({
            "Rank": row["Rank"],
            "No": no,
            "Hybrid Score": round(hybrid_total, 3),
            "Confidence": row["Confidence"],
            "Main Source": main_source,
            "Stat": round(stat, 3),
            "Stat %": stat_pct,
            "Position": round(pos, 3),
            "Position %": pos_pct,
            "Pair": round(pair, 3),
            "Pair %": pair_pct,
            "Theory": round(theory, 3),
            "Theory %": theory_pct,
            "Hybrid Boost": round(boost, 3),
            "Boost %": boost_pct,
        })
    return pd.DataFrame(rows)

def cold_rebound_engine(history, window=100):
    recent = history.tail(window)
    rows = []
    expected = (len(recent) * 12) / 10 if len(recent) else 0
    for d in "0123456789":
        actual = 0
        gap = 0
        found = False

        for _, row in recent.iterrows():
            actual += (pad4(row["first"]) + pad4(row["second"]) + pad4(row["third"])).count(d)

        for _, row in recent.iloc[::-1].iterrows():
            text = pad4(row["first"]) + pad4(row["second"]) + pad4(row["third"])
            if d in text:
                found = True
                break
            gap += 1

        deficit = expected - actual
        rebound_score = round(max(0, deficit) + (gap * 1.5), 3)
        rows.append({
            "Digit": d,
            "Window": window,
            "Expected": round(expected, 2),
            "Actual": actual,
            "Deficit": round(deficit, 2),
            "Gap": gap if found else len(recent),
            "Cold Rebound Score": rebound_score,
        })

    return pd.DataFrame(rows).sort_values("Cold Rebound Score", ascending=False).reset_index(drop=True)

def hot_reversal_detector(history, window=30):
    recent = hot_digit_analysis(history, window=window)
    rows = []
    for _, row in recent.iterrows():
        digit = row["Digit"]
        count = float(row["Count"])
        prev = float(row["Prev Count"])
        diff = float(row["Diff"])
        if count > prev and count >= recent["Count"].mean():
            signal = "Hot Rising"
            reversal_risk = round(max(0, diff) / max(1, count) * 100, 1)
        elif count < prev and prev >= recent["Prev Count"].mean():
            signal = "Cooling Down"
            reversal_risk = round(abs(diff) / max(1, prev) * 100, 1)
        else:
            signal = "Neutral"
            reversal_risk = 0.0
        rows.append({
            "Digit": digit,
            "Current": int(count),
            "Previous": int(prev),
            "Diff": int(diff),
            "Signal": signal,
            "Reversal Risk %": reversal_risk,
        })
    return pd.DataFrame(rows).sort_values(["Signal", "Reversal Risk %"], ascending=[True, False]).reset_index(drop=True)

def _pairs_of_no(no):
    s = str(no).zfill(4)
    return {s[i:i+2] for i in range(3)} | {s[0]+s[2], s[0]+s[3], s[1]+s[3]}

def _position_match_score(pred_no, actual_numbers):
    pred = str(pred_no).zfill(4)
    best = 0
    for actual in actual_numbers:
        a = str(actual).zfill(4)
        best = max(best, sum(1 for i in range(4) if pred[i] == a[i]))
    return best

def model_accuracy_tracker(history, lookback=100):
    """
    V17.1 Fix:
    Accuracy lebih ketat:
    - Statistik / Pair / Theory: hit jika candidate Top20 share sekurang-kurangnya 2 pair dengan mana-mana result sebenar.
    - Position: hit jika sekurang-kurangnya 2 digit berada pada posisi sama dengan mana-mana result sebenar.
    Ini masih backtest ringkas, tetapi jauh lebih ketat daripada overlap digit biasa.
    """
    if len(history) < 30:
        return pd.DataFrame({
            "Model": ["Statistik", "Peralihan Posisi", "Pasangan", "Model No Double"],
            "Lookback": [0, 0, 0, 0],
            "Hits": [0, 0, 0, 0],
            "Accuracy %": [0, 0, 0, 0],
        })

    max_i = len(history) - 1
    min_i = max(20, len(history) - lookback)
    models = {
        "Statistik": {"hits": 0, "tests": 0},
        "Peralihan Posisi": {"hits": 0, "tests": 0},
        "Pasangan": {"hits": 0, "tests": 0},
        "Model No Double": {"hits": 0, "tests": 0},
    }

    for i in range(min_i, max_i + 1):
        past = history.iloc[:i].copy()
        target = history.iloc[i]
        if past.empty:
            continue

        try:
            prev = past.iloc[-1]
            res = generate(past, prev["first"], prev["second"], prev["third"])
        except Exception:
            continue

        actual_numbers = [pad4(target["first"]), pad4(target["second"]), pad4(target["third"])]
        actual_pairs = set()
        for actual in actual_numbers:
            actual_pairs |= _pairs_of_no(actual)

        model_tables = {
            "Statistik": res["stat"],
            "Peralihan Posisi": res["position"],
            "Pasangan": res["pair"],
            "Model No Double": res["theory"],
        }

        for model_name, df in model_tables.items():
            if df is None or df.empty:
                continue

            top_candidates = df["No"].head(20).astype(str).str.zfill(4).tolist()
            hit = False

            for cand in top_candidates:
                if model_name == "Peralihan Posisi":
                    if _position_match_score(cand, actual_numbers) >= 2:
                        hit = True
                        break
                else:
                    cand_pairs = _pairs_of_no(cand)
                    if len(cand_pairs.intersection(actual_pairs)) >= 2:
                        hit = True
                        break

            models[model_name]["hits"] += int(hit)
            models[model_name]["tests"] += 1

    rows = []
    for model_name, v in models.items():
        tests = v["tests"]
        hits = v["hits"]
        acc = round((hits / tests) * 100, 1) if tests else 0
        rows.append({"Model": model_name, "Lookback": tests, "Hits": hits, "Accuracy %": acc})

    return pd.DataFrame(rows).sort_values("Accuracy %", ascending=False).reset_index(drop=True)

def adaptive_weight_engine(result, accuracy_df=None):
    if accuracy_df is not None and not accuracy_df.empty and accuracy_df["Accuracy %"].sum() > 0:
        rows = []
        total_acc = accuracy_df["Accuracy %"].sum()
        for _, row in accuracy_df.iterrows():
            rows.append({
                "Model": row["Model"],
                "Accuracy %": row["Accuracy %"],
                "Suggested Weight %": round((row["Accuracy %"] / total_acc) * 100, 1),
                "Basis": "Strict Backtest",
            })
        return pd.DataFrame(rows).sort_values("Suggested Weight %", ascending=False).reset_index(drop=True)

    return pd.DataFrame({
        "Model": ["Statistik", "Peralihan Posisi", "Pasangan", "Model No Double"],
        "Accuracy %": [0, 0, 0, 0],
        "Suggested Weight %": [25, 25, 25, 25],
        "Basis": ["Default"] * 4,
    })

def champion_number_engine(result, cold_rebound_df, hot_reversal_df, stability_df=None, top_n=20):
    """
    V17.2:
    Champion = 60% Hybrid + 15% Cold Rebound + 10% Hot Trend + 15% PSI.
    PSI membantu nombor yang konsisten naik ranking.
    """
    cold_scores = dict(zip(cold_rebound_df["Digit"], cold_rebound_df["Cold Rebound Score"])) if cold_rebound_df is not None else {}
    hot_signals = dict(zip(hot_reversal_df["Digit"], hot_reversal_df["Signal"])) if hot_reversal_df is not None else {}
    psi_map = dict(zip(stability_df["No"].astype(str).str.zfill(4), stability_df["PSI"])) if stability_df is not None and not stability_df.empty else {}

    hybrid = result["hybrid_all"].head(100).copy()
    max_hybrid = float(hybrid["Score"].max()) if not hybrid.empty else 1
    max_cold_digit = max(cold_scores.values()) if cold_scores else 1

    rows = []
    for _, row in hybrid.iterrows():
        no = str(row["No"]).zfill(4)
        digits = list(no)

        hybrid_norm = (float(row["Score"]) / max_hybrid) * 100 if max_hybrid else 0

        cold_raw = sum(float(cold_scores.get(d, 0)) for d in digits) / 4
        cold_norm = (cold_raw / max_cold_digit) * 100 if max_cold_digit else 0

        hot_score = 0
        for d in digits:
            sig = hot_signals.get(d, "Neutral")
            if sig == "Hot Rising":
                hot_score += 25
            elif sig == "Cooling Down":
                hot_score -= 15
        hot_norm = max(0, min(100, 50 + hot_score / 4))

        psi = float(psi_map.get(no, 0))

        champion_score = (
            (hybrid_norm * 0.60)
            + (cold_norm * 0.15)
            + (hot_norm * 0.10)
            + (psi * 0.15)
        )

        rows.append({
            "No": no,
            "Hybrid Norm": round(hybrid_norm, 2),
            "Cold Norm": round(cold_norm, 2),
            "Hot Norm": round(hot_norm, 2),
            "PSI": round(psi, 1),
            "Champion Score": round(champion_score, 3),
        })

    df = pd.DataFrame(rows).sort_values("Champion Score", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df.head(top_n)



def champion_engine_v19(result, accuracy_df=None, top_each=10, top_n=30):
    """
    V19 Champion Engine:
    Ambil Top 10 dari setiap model utama dan beri markah berdasarkan:
    - Model accuracy
    - Rank bonus
    - Original model score
    - Hybrid score
    - Existing confidence
    """
    model_frames = {
        "Statistik": result.get("stat", pd.DataFrame()).head(top_each),
        "Peralihan Posisi": result.get("position", pd.DataFrame()).head(top_each),
        "Pasangan": result.get("pair", pd.DataFrame()).head(top_each),
        "Model No Double": result.get("theory", pd.DataFrame()).head(top_each),
    }

    default_acc = {
        "Statistik": 53.0,
        "Peralihan Posisi": 53.0,
        "Pasangan": 65.7,
        "Model No Double": 84.8,
    }

    acc_map = default_acc.copy()
    if accuracy_df is not None and not accuracy_df.empty:
        if "Model" in accuracy_df.columns and "Accuracy %" in accuracy_df.columns:
            for _, r in accuracy_df.iterrows():
                m = str(r["Model"])
                if m in acc_map:
                    try:
                        acc_map[m] = float(r["Accuracy %"])
                    except Exception:
                        pass

    hybrid_df = result.get("hybrid_all", pd.DataFrame()).copy()
    hybrid_map = {}
    conf_map = {}
    if not hybrid_df.empty and "No" in hybrid_df.columns:
        for _, r in hybrid_df.iterrows():
            no = str(r["No"]).zfill(4)
            hybrid_map[no] = float(r.get("Score", 0))
            conf_map[no] = float(r.get("Confidence", 0))

    max_hybrid = max(hybrid_map.values()) if hybrid_map else 1

    rows = {}
    for model_name, df in model_frames.items():
        if df is None or df.empty or "No" not in df.columns:
            continue

        max_model_score = float(df["Score"].max()) if "Score" in df.columns and len(df) else 1
        model_acc = acc_map.get(model_name, 50)

        for idx, r in df.iterrows():
            no = str(r["No"]).zfill(4)
            rank = int(r["Rank"]) if "Rank" in df.columns else idx + 1
            model_score = float(r["Score"]) if "Score" in df.columns else 0

            model_score_norm = (model_score / max_model_score * 100) if max_model_score else 0
            rank_bonus = max(0, (top_each + 1 - rank) / top_each * 100)
            accuracy_bonus = model_acc
            hybrid_bonus = (hybrid_map.get(no, 0) / max_hybrid * 100) if max_hybrid else 0
            confidence_bonus = conf_map.get(no, 0)

            # Formula praktikal:
            # model asal dan accuracy paling penting
            contribution = (
                model_score_norm * 0.35 +
                rank_bonus * 0.25 +
                accuracy_bonus * 0.25 +
                hybrid_bonus * 0.10 +
                confidence_bonus * 0.05
            )

            if no not in rows:
                rows[no] = {
                    "No": no,
                    "Supported By": [],
                    "Support Count": 0,
                    "Champion Score": 0.0,
                    "Best Rank": rank,
                    "Best Model": model_name,
                    "Best Model Score": model_score,
                    "Model Detail": [],
                    "Hybrid Score": hybrid_map.get(no, 0),
                    "Confidence": confidence_bonus,
                }

            rows[no]["Supported By"].append(model_name)
            rows[no]["Support Count"] += 1
            rows[no]["Champion Score"] += contribution
            rows[no]["BestRankTemp"] = min(rows[no].get("BestRankTemp", rank), rank)

            if rank < rows[no]["Best Rank"]:
                rows[no]["Best Rank"] = rank
                rows[no]["Best Model"] = model_name
                rows[no]["Best Model Score"] = model_score

            rows[no]["Model Detail"].append(f"{model_name}#{rank}")

    out = []
    for no, d in rows.items():
        support_bonus = d["Support Count"] * 8
        final = d["Champion Score"] + support_bonus - (d["Best Rank"] * 0.25)

        practical_conf = min(95, round(50 + d["Support Count"] * 8 + final / 18, 1))

        out.append({
            "No": no,
            "Champion Score": round(final, 3),
            "Support Count": d["Support Count"],
            "Supported By": " + ".join(d["Supported By"]),
            "Best Model": d["Best Model"],
            "Best Rank": d["Best Rank"],
            "Hybrid Score": round(d["Hybrid Score"], 3),
            "Confidence": practical_conf,
            "Model Detail": ", ".join(d["Model Detail"]),
        })

    if not out:
        return pd.DataFrame(columns=["Rank", "No", "Champion Score", "Support Count", "Supported By", "Best Model", "Best Rank", "Confidence"])

    df = pd.DataFrame(out).sort_values(
        ["Support Count", "Champion Score", "Best Rank"],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df.head(top_n)


def champion_v19_audit(champion_df):
    if champion_df is None or champion_df.empty:
        return pd.DataFrame()

    rows = []
    for model in ["Statistik", "Peralihan Posisi", "Pasangan", "Model No Double"]:
        count = champion_df["Supported By"].astype(str).str.contains(model, regex=False).sum()
        rows.append({"Item": model, "Count": int(count)})

    rows.append({"Item": "Support Count 2+", "Count": int((champion_df["Support Count"] >= 2).sum())})
    rows.append({"Item": "Support Count 3+", "Count": int((champion_df["Support Count"] >= 3).sum())})
    rows.append({"Item": "Average Confidence", "Count": round(float(champion_df["Confidence"].mean()), 1)})
    return pd.DataFrame(rows)



def consensus_boost_v19_1(result, champion_df=None, top_each=30, top_n=30):
    """
    V19.1 Consensus Boost:
    Tujuan: cari nombor yang ada sokongan lebih daripada satu sumber.
    Sumber dikira:
    - Statistik top_each
    - Peralihan Posisi top_each
    - Pasangan top_each
    - Model No Double top_each
    - Hybrid top_each

    Ini bukan menggantikan Champion V19 sepenuhnya.
    Ia jadual sokongan tambahan supaya pilihan nombor lebih mudah dibuat.
    """
    sources = {
        "Statistik": result.get("stat", pd.DataFrame()).head(top_each),
        "Peralihan Posisi": result.get("position", pd.DataFrame()).head(top_each),
        "Pasangan": result.get("pair", pd.DataFrame()).head(top_each),
        "Model No Double": result.get("theory", pd.DataFrame()).head(top_each),
        "Hybrid": result.get("hybrid_all", pd.DataFrame()).head(top_each),
    }

    rows = {}

    for source_name, df in sources.items():
        if df is None or df.empty or "No" not in df.columns:
            continue

        max_score = float(df["Score"].max()) if "Score" in df.columns and len(df) else 1.0

        for idx, r in df.iterrows():
            no = str(r["No"]).zfill(4)
            rank = int(r["Rank"]) if "Rank" in df.columns else idx + 1
            score = float(r["Score"]) if "Score" in df.columns else 0.0
            score_norm = (score / max_score * 100) if max_score else 0.0
            rank_bonus = max(0.0, (top_each + 1 - rank) / top_each * 100)

            # Setiap source menyumbang secara sederhana.
            # Rank lebih penting daripada score mentah.
            contribution = (rank_bonus * 0.6) + (score_norm * 0.4)

            if no not in rows:
                rows[no] = {
                    "No": no,
                    "Support Count": 0,
                    "Supported By": [],
                    "Best Rank": rank,
                    "Raw Consensus Score": 0.0,
                    "Detail": [],
                }

            rows[no]["Support Count"] += 1
            rows[no]["Supported By"].append(source_name)
            rows[no]["Best Rank"] = min(rows[no]["Best Rank"], rank)
            rows[no]["Raw Consensus Score"] += contribution
            rows[no]["Detail"].append(f"{source_name}#{rank}")

    # Bonus sokongan sebenar
    out = []
    champion_map = {}
    if champion_df is not None and not champion_df.empty and "No" in champion_df.columns:
        for _, r in champion_df.iterrows():
            champion_map[str(r["No"]).zfill(4)] = {
                "Champion Rank": int(r.get("Rank", 999)),
                "Champion Score": float(r.get("Champion Score", 0)),
                "Champion Confidence": float(r.get("Confidence", 0)),
            }

    for no, d in rows.items():
        support_count = int(d["Support Count"])
        support_bonus = support_count * 20
        best_rank_bonus = max(0, 31 - int(d["Best Rank"]))
        champion_info = champion_map.get(no, {"Champion Rank": 999, "Champion Score": 0, "Champion Confidence": 0})
        champion_bonus = max(0, 41 - champion_info["Champion Rank"]) if champion_info["Champion Rank"] != 999 else 0

        final_score = d["Raw Consensus Score"] + support_bonus + best_rank_bonus + champion_bonus
        confidence = min(95, round(45 + support_count * 10 + final_score / 20, 1))

        out.append({
            "No": no,
            "Support Count": support_count,
            "Supported By": " + ".join(d["Supported By"]),
            "Best Rank": int(d["Best Rank"]),
            "Consensus Score": round(final_score, 3),
            "Confidence": confidence,
            "Champion Rank": champion_info["Champion Rank"] if champion_info["Champion Rank"] != 999 else "-",
            "Champion Score": round(champion_info["Champion Score"], 3),
            "Detail": ", ".join(d["Detail"]),
        })

    if not out:
        return pd.DataFrame(columns=["Rank", "No", "Support Count", "Supported By", "Consensus Score", "Confidence"])

    df = pd.DataFrame(out).sort_values(
        ["Support Count", "Consensus Score", "Best Rank"],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df.head(top_n)


def consensus_boost_audit_v19_1(consensus_df):
    if consensus_df is None or consensus_df.empty:
        return pd.DataFrame(columns=["Item", "Count"])

    return pd.DataFrame([
        {"Item": "Nombor dengan 1 sokongan", "Count": int((consensus_df["Support Count"] == 1).sum())},
        {"Item": "Nombor dengan 2+ sokongan", "Count": int((consensus_df["Support Count"] >= 2).sum())},
        {"Item": "Nombor dengan 3+ sokongan", "Count": int((consensus_df["Support Count"] >= 3).sum())},
        {"Item": "Purata Confidence", "Count": round(float(consensus_df["Confidence"].mean()), 1)},
    ])


def make_prediction_report_excel(result, hot_df, cold_df, inputs):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        pd.DataFrame([inputs]).to_excel(writer, sheet_name="Input", index=False)
        result["hybrid_all"].to_excel(writer, sheet_name="Top Hybrid", index=False)
        if "champion_v19" in result:
            result["champion_v19"].to_excel(writer, sheet_name="V19 Champion Picks", index=False)
        if "champion_v19_audit" in result:
            result["champion_v19_audit"].to_excel(writer, sheet_name="V19 Audit", index=False)
        if "consensus_boost_v19_1" in result:
            result["consensus_boost_v19_1"].to_excel(writer, sheet_name="V19.1 Consensus Boost", index=False)
        if "consensus_boost_audit_v19_1" in result:
            result["consensus_boost_audit_v19_1"].to_excel(writer, sheet_name="V19.1 Consensus Audit", index=False)
        result["stat"].to_excel(writer, sheet_name="Model Statistik", index=False)
        result["position"].to_excel(writer, sheet_name="Model Peralihan", index=False)
        result["pair"].to_excel(writer, sheet_name="Model Pasangan", index=False)
        result["theory"].to_excel(writer, sheet_name="Model No Double", index=False)
        hot_df.to_excel(writer, sheet_name="Hot Digits", index=False)
        cold_df.to_excel(writer, sheet_name="Cold Digits", index=False)
        audit = result["audit"]
        pd.DataFrame({
            "Missing Digits": [" ".join(audit["missing"])],
            "Top Recent": [" ".join(audit["top_recent"])],
            "Top Missing Next": [" ".join(audit["top_missing_next"])],
        }).to_excel(writer, sheet_name="Audit Ringkas", index=False)
        pd.DataFrame(audit["top_pairs"], columns=["Pair", "Warisan %"]).to_excel(writer, sheet_name="Top Pairs", index=False)
    bio.seek(0)
    return bio



def digit_family_key(n):
    try:
        return "".join(sorted(pad4(n)))
    except Exception:
        return ""

def digit_family_rotation_df(model_sources, latest_nums=None, limit=40):
    """
    Cari nombor yang berkongsi keluarga digit yang sama / hampir sama.
    Ini bukan ramalan baharu; hanya lapisan audit signal.
    """
    rows = []
    latest_families = set()
    latest_nums = latest_nums or []
    for n in latest_nums:
        latest_families.add(digit_family_key(n))

    seen = {}
    for source, nums in model_sources:
        for rank, n in enumerate(nums[:limit], start=1):
            s = pad4(n)
            key = digit_family_key(s)
            if not key:
                continue
            if key not in seen:
                seen[key] = {"Family": key, "Examples": [], "Sources": set(), "Score": 0}
            seen[key]["Examples"].append(s)
            seen[key]["Sources"].add(source)
            seen[key]["Score"] += max(1, 15 - min(rank, 14))

    for key, item in seen.items():
        examples = list(dict.fromkeys(item["Examples"]))[:8]
        sources = sorted(item["Sources"])
        rows.append({
            "Family": key,
            "Signal": len(sources),
            "Strength": "⭐" * min(len(sources), 5),
            "Examples": " / ".join(examples),
            "Models": ", ".join(sources),
            "Matched Latest": "YES" if key in latest_families else "",
            "Score": item["Score"],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Signal", "Score"], ascending=[False, False]).reset_index(drop=True)

def double_double_type(n):
    s = pad4(n)
    from collections import Counter
    c = Counter(s)
    vals = sorted(c.values(), reverse=True)
    if vals == [2, 2]:
        # ABAB / ABBA / AABB-ish pattern labels
        if s[0] == s[2] and s[1] == s[3]:
            return "ABAB"
        if s[0] == s[3] and s[1] == s[2]:
            return "ABBA"
        return "AABB"
    return ""

def build_double_double_watch(model_sources, limit=50):
    rows = []
    seen = {}
    for source, nums in model_sources:
        for rank, n in enumerate(nums[:limit], start=1):
            s = pad4(n)
            typ = double_double_type(s)
            if not typ:
                continue
            if s not in seen:
                seen[s] = {"No": s, "Pattern": typ, "Sources": set(), "Best Rank": rank}
            seen[s]["Sources"].add(source)
            seen[s]["Best Rank"] = min(seen[s]["Best Rank"], rank)
    for s, item in seen.items():
        sources = sorted(item["Sources"])
        rows.append({
            "No": s,
            "Pattern": item["Pattern"],
            "Signal": len(sources),
            "Strength": "⭐" * min(len(sources), 5),
            "Models": ", ".join(sources),
            "Best Rank": item["Best Rank"],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Signal", "Best Rank"], ascending=[False, True]).reset_index(drop=True)

def triple_type(n):
    s = pad4(n)
    from collections import Counter
    c = Counter(s)
    for d, cnt in c.items():
        if cnt >= 3:
            outsider = "".join([x for x in s if x != d])
            return d * 3, outsider
    return "", ""

def build_no_triple_watch(model_sources, limit=50):
    rows = []
    seen = {}
    for source, nums in model_sources:
        for rank, n in enumerate(nums[:limit], start=1):
            s = pad4(n)
            triple, outsider = triple_type(s)
            if not triple:
                continue
            if s not in seen:
                seen[s] = {"No": s, "Triple": triple, "Outsider": outsider, "Sources": set(), "Best Rank": rank}
            seen[s]["Sources"].add(source)
            seen[s]["Best Rank"] = min(seen[s]["Best Rank"], rank)
    for s, item in seen.items():
        sources = sorted(item["Sources"])
        rows.append({
            "No": s,
            "Triple": item["Triple"],
            "Outsider": item["Outsider"],
            "Signal": len(sources),
            "Strength": "⭐" * min(len(sources), 5),
            "Models": ", ".join(sources),
            "Best Rank": item["Best Rank"],
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Signal", "Best Rank"], ascending=[False, True]).reset_index(drop=True)



def structure_type(n):
    try:
        s = pad4(n)
        from collections import Counter
        counts = sorted(Counter(s).values(), reverse=True)
        if counts == [4]:
            return "Quadruple"
        if counts == [3, 1]:
            return "No Triple"
        if counts == [2, 2]:
            if s[0] == s[2] and s[1] == s[3]:
                return "Double-Double ABAB"
            if s[0] == s[3] and s[1] == s[2]:
                return "Double-Double ABBA"
            return "Double-Double AABB"
        if counts == [2, 1, 1]:
            return "Single Double"
        return "No Double"
    except Exception:
        return ""




def unique_permutations_4(n):
    """Return all unique 4-digit arrangements from a candidate family."""
    import itertools
    s = pad4(n)
    return sorted(set("".join(p) for p in itertools.permutations(s, 4)))

@st.cache_data(show_spinner=False)
def build_arrangement_stats_v30(history):
    """
    Cache statistik arrangement supaya tidak scan history 34 tahun berulang kali
    untuk setiap permutation.
    """
    from collections import Counter, defaultdict

    cols = ["first", "second", "third"]
    all_nums = []
    for _, row in history.iterrows():
        for c in cols:
            all_nums.append(pad4(row[c]))

    exact_counter = Counter(all_nums)

    digit_total = Counter()
    pos_digit = Counter()
    pair_total = Counter()
    pair_pos = Counter()

    for x in all_nums:
        if len(x) != 4:
            continue

        for d in "0123456789":
            if d in x:
                digit_total[d] += 1

        for i, d in enumerate(x):
            pos_digit[(i, d)] += 1

        for a in "0123456789":
            for b in "0123456789":
                if a in x and b in x:
                    pair_total[a + b] += 1

        for i in range(3):
            pair_pos[(i, x[i:i+2])] += 1

    return {
        "exact_counter": exact_counter,
        "digit_total": digit_total,
        "pos_digit": pos_digit,
        "pair_total": pair_total,
        "pair_pos": pair_pos,
    }


def arrangement_score_v29(candidate, history):
    """
    Arrangement score v29 optimized.
    Formula asal dikekalkan, tetapi statistik history dicache sekali sahaja.
    """
    try:
        s = pad4(candidate)
        if history is None or history.empty:
            return 0, "No history"

        stats = build_arrangement_stats_v30(history)

        exact_count = stats["exact_counter"].get(s, 0)

        pos_score = 0
        for i, d in enumerate(s):
            total_d = stats["digit_total"].get(d, 0)
            pos_d = stats["pos_digit"].get((i, d), 0)
            if total_d:
                pos_score += (pos_d / max(total_d, 1)) * 10

        pair_score = 0
        pair_notes = []
        for i in range(3):
            p = s[i:i+2]
            total_p = stats["pair_total"].get(p, 0)
            pos_p = stats["pair_pos"].get((i, p), 0)
            if total_p:
                val = (pos_p / max(total_p, 1)) * 18
                pair_score += val
                if val >= 1.5:
                    pair_notes.append(f"{p}@{i+1}-{i+2}")

        double_score = 0
        for i in range(3):
            if s[i] == s[i+1]:
                double_score += 8
                pair_notes.append(f"double {s[i]}@{i+1}-{i+2}")

        exact_score = exact_count * 12
        score = round(exact_score + pos_score + pair_score + double_score, 2)

        reason = []
        if exact_count:
            reason.append(f"history {exact_count}x")
        if pair_notes:
            reason.append("pair " + ", ".join(pair_notes[:4]))
        reason.append(f"pos {round(pos_score,1)}")
        return score, "; ".join(reason)
    except Exception:
        return 0, "-"

def build_arrangement_engine_v29(family_no, history, top_n=8):
    rows = []
    for cand in unique_permutations_4(family_no):
        score, reason = arrangement_score_v29(cand, history)
        rows.append({
            "Arrangement": cand,
            "Score": score,
            "Reason": reason,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Score", "Arrangement"], ascending=[False, True]).head(top_n).reset_index(drop=True)



def completion_arrangements_lite(family, top_n=12):
    """
    Arrangement ringkas tanpa scan history.
    Untuk family unik seperti 0248, letak susunan completion-style di depan:
    8240 / 8204 / 8024 / 8042 / 8420 / 8402 ...
    Untuk family double seperti 0244, letak susunan double yang mudah dibaca.
    """
    import itertools
    s = "".join(sorted(str(family).zfill(4)[-4:]))
    digits = list(s)
    perms = sorted(set("".join(p) for p in itertools.permutations(digits, 4)))

    counts = {d: digits.count(d) for d in set(digits)}

    preferred = []
    if max(counts.values()) >= 2:
        # Double family: kekalkan semua permutation unik tetapi susun yang bermula rendah dahulu.
        preferred = perms
    else:
        a, b, c, d = digits[0], digits[1], digits[2], digits[3]
        preferred = [
            d+b+c+a, d+b+a+c, d+a+b+c, d+a+c+b, d+c+b+a, d+c+a+b,
            b+c+d+a, b+c+a+d, b+a+d+c, c+b+d+a, a+d+b+c, a+d+c+b,
        ]
        preferred = [x for x in preferred if x in perms]

    final = []
    for x in preferred + perms:
        if x not in final:
            final.append(x)

    return final[:top_n]


def build_family_completion_lite_v30(model_sources, top_families=12, top_arrangements=12):
    """
    Family Completion Lite.
    Audit tambahan sahaja:
    - guna semua 50 nombor dari 4 model
    - tidak scan history 34 tahun
    - tidak panggil Arrangement Engine
    - cari 3D overlap, double pressure, dan hidden family
    """
    try:
        from collections import defaultdict, Counter
        import itertools

        source_weight = {
            "No Double": 5,
            "Pasangan": 5,
            "Peralihan": 3,
            "Statistik": 2,
        }

        items = []
        for source, nums in model_sources:
            for rank, n in enumerate(nums, start=1):
                s = pad4(n)
                if not s:
                    continue
                items.append({
                    "source": source,
                    "no": s,
                    "rank": rank,
                    "digits": set(s),
                    "count": Counter(s),
                    "family": "".join(sorted(s)),
                })

        fam = defaultdict(lambda: {
            "Family": "",
            "Score": 0.0,
            "Support": set(),
            "Sources": set(),
            "Reason": [],
            "Exact Model Family": 0,
        })

        def overlap_multiset(family, item):
            fc = Counter(family)
            return sum(min(fc[d], item["count"].get(d, 0)) for d in fc)

        def add_family(f, score, item_list, reason):
            f = "".join(sorted(str(f).zfill(4)[-4:]))
            rec = fam[f]
            rec["Family"] = f
            rec["Score"] += float(score)
            for it in item_list:
                rec["Support"].add(it["no"])
                rec["Sources"].add(it["source"])
            if reason not in rec["Reason"]:
                rec["Reason"].append(reason)

        # exact model family count
        exact_count = Counter(it["family"] for it in items)

        # Rule 1: Pairwise completion daripada semua 50 nombor
        for a, b in itertools.combinations(items, 2):
            common = a["digits"] & b["digits"]
            union = sorted(a["digits"] | b["digits"])

            if len(common) >= 2 and len(union) >= 4:
                for comb in itertools.combinations(union, 4):
                    f = "".join(sorted(comb))
                    score = (
                        len(common) * 7
                        + source_weight.get(a["source"], 2)
                        + source_weight.get(b["source"], 2)
                    )
                    if a["source"] != b["source"]:
                        score += 4
                    add_family(f, score, [a, b], f"overlap {''.join(sorted(common))}")

            # Rule 2: double pressure
            for item1, item2 in [(a, b), (b, a)]:
                doubles = [d for d, c in item1["count"].items() if c >= 2]
                for d in doubles:
                    support_digits = sorted((item1["digits"] | item2["digits"]) - {d})
                    if len(support_digits) >= 2:
                        for extra in itertools.combinations(support_digits, 2):
                            f = "".join(sorted([d, d] + list(extra)))
                            score = 22 + source_weight.get(item1["source"], 2) + source_weight.get(item2["source"], 2)
                            add_family(f, score, [item1, item2], f"double {d}")

        # Rule 3: 3D pressure terhadap candidate family
        all_digits = sorted(set().union(*[it["digits"] for it in items]))
        candidate_families = set()

        for comb in itertools.combinations(all_digits, 4):
            candidate_families.add("".join(sorted(comb)))

        for d in all_digits:
            others = [x for x in all_digits if x != d]
            for extra in itertools.combinations(others, 2):
                candidate_families.add("".join(sorted([d, d] + list(extra))))

        for f in candidate_families:
            supporters = []
            sources = set()
            score = 0
            for it in items:
                ov = overlap_multiset(f, it)
                if ov >= 3:
                    supporters.append(it)
                    sources.add(it["source"])
                    score += ov * 6 + source_weight.get(it["source"], 2)

            if len({it["no"] for it in supporters}) >= 2:
                score += len(sources) * 5
                add_family(f, score, supporters[:10], f"3D pressure {len({it['no'] for it in supporters})} nos")

        rows = []
        for f, rec in fam.items():
            rec["Exact Model Family"] = exact_count.get(f, 0)

            # Hidden family bonus: family yang tiada sebagai nombor model asal tetapi ada 3D support.
            hidden_bonus = 18 if rec["Exact Model Family"] == 0 else 0
            exact_penalty = rec["Exact Model Family"] * 8

            arrangements = completion_arrangements_lite(f, top_n=top_arrangements)

            rows.append({
                "Family": f,
                "Score": round(rec["Score"] + hidden_bonus - exact_penalty, 2),
                "Support Count": len(rec["Support"]),
                "Sources": ", ".join(sorted(rec["Sources"])),
                "Exact Model Family": rec["Exact Model Family"],
                "Top Arrangement": " / ".join(arrangements),
                "Support Nos": " / ".join(sorted(rec["Support"])[:12]),
                "Reason": " | ".join(rec["Reason"][:5]),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Utamakan support sebenar dan hidden family, bukan sekadar digit paling popular.
        df = df.sort_values(
            ["Support Count", "Exact Model Family", "Score", "Family"],
            ascending=[False, True, False, True]
        ).head(top_families).reset_index(drop=True)

        return df

    except Exception:
        return pd.DataFrame()



def build_anchor_cluster_convergence_v30(model_sources, top_families=10):
    """
    Experimental:
    Anchor (2 digits) -> Cluster -> Hidden Family.
    Uses only current 50 generated numbers.
    """
    from collections import defaultdict, Counter
    import itertools
    import pandas as pd

    items = []
    exact_families = set()

    for source, nums in model_sources:
        for n in nums:
            s = pad4(n)
            fam = "".join(sorted(s))
            exact_families.add(fam)
            items.append({
                "source": source,
                "no": s,
                "digits": set(s),
            })

    fam_map = defaultdict(lambda: {
        "Family": "",
        "Support": set(),
        "Anchors": set(),
        "Clusters": set(),
        "Score": 0,
    })

    # Build anchor clusters from all 2-digit combinations
    pair_map = defaultdict(list)
    for it in items:
        for p in itertools.combinations(sorted(it["digits"]), 2):
            pair_map["".join(p)].append(it)

    for anchor, cluster in pair_map.items():
        if len(cluster) < 3:
            continue

        anchor_set = set(anchor)
        digit_freq = Counter()

        # count extra digits outside anchor
        for it in cluster:
            extras = it["digits"] - anchor_set
            for d in extras:
                digit_freq[d] += 1

        # keep extras that appear >=2 times
        extras = [d for d, c in digit_freq.items() if c >= 2]

        # need at least 2 supporting digits
        if len(extras) < 2:
            continue

        for ex2 in itertools.combinations(sorted(extras), 2):
            fam_digits = list(anchor_set) + list(ex2)
            if len(set(fam_digits)) != 4:
                continue

            fam = "".join(sorted(fam_digits))
            if fam in exact_families:
                continue

            rec = fam_map[fam]
            rec["Family"] = fam
            rec["Anchors"].add(anchor)

            support = []
            for it in cluster:
                overlap = len(set(fam_digits) & it["digits"])
                if overlap >= 3:
                    support.append(it["no"])
                    rec["Clusters"].add(it["no"])

            if len(set(support)) >= 2:
                rec["Support"].update(support)
                rec["Score"] += len(set(support)) * 10 + len(cluster)

    rows = []
    for fam, rec in fam_map.items():
        if not rec["Support"]:
            continue

        rows.append({
            "Family": fam,
            "Score": rec["Score"],
            "Support Count": len(rec["Support"]),
            "Anchor": ", ".join(sorted(rec["Anchors"])),
            "Support Nos": " / ".join(sorted(rec["Support"])),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return df.sort_values(
        ["Support Count", "Score", "Family"],
        ascending=[False, False, True]
    ).head(top_families).reset_index(drop=True)



def build_pair_assist_all_anchor_safe_v30(anchor_families, result_pairs):
    """
    Pair Assist All Anchor SAFE.
    - Ambil SEMUA family dari Anchor Cluster.
    - Gabung dengan SEMUA pair result input.
    - Output grouped by anchor family.
    - Tiada score/support/sources.
    """
    import itertools
    import pandas as pd

    clean_anchor = []
    for f in anchor_families or []:
        s = "".join(sorted(str(f).strip().zfill(4)[-4:]))
        if len(s) == 4 and s not in clean_anchor:
            clean_anchor.append(s)

    clean_pairs = []
    for p in result_pairs or []:
        pair = str(p).strip().zfill(2)[-2:]
        if len(pair) == 2 and pair.isdigit() and pair not in clean_pairs:
            clean_pairs.append(pair)

    rows = []
    copy_lines = []

    for fam in clean_anchor:
        chars = list(fam)
        produced = []
        detail = []

        for pair in clean_pairs:
            pair_chars = list(pair)

            for idxs in itertools.combinations(range(4), 2):
                new_chars = pair_chars + [chars[idxs[0]], chars[idxs[1]]]
                new_fam = "".join(sorted(new_chars))

                if len(new_fam) != 4:
                    continue
                if new_fam == fam:
                    continue

                if new_fam not in produced:
                    produced.append(new_fam)

                reason = f"{fam} + {pair} -> {new_fam}"
                if reason not in detail:
                    detail.append(reason)

        if produced:
            copy_lines.append(f"{fam}: {' / '.join(produced[:20])}")
            rows.append({
                "Anchor Family": fam,
                "New Family": " / ".join(produced[:20]),
                "Detail": " / ".join(detail[:20]),
            })

    return pd.DataFrame(rows), copy_lines




def build_anchor_density_signal_v31(pair_assist_df, min_support=2, top_n=30):
    """
    V31.4 Anchor Density Signal.
    Observation layer sahaja.
    Kira nombor/family Pair Assist yang muncul daripada berapa banyak anchor.
    Tidak ubah Pair Assist, ranking, AI Pick atau model utama.
    """
    import pandas as pd
    from collections import defaultdict

    if pair_assist_df is None or pair_assist_df.empty:
        return pd.DataFrame(), ""

    anchor_map = defaultdict(set)

    for _, row in pair_assist_df.iterrows():
        anchor = str(row.get("Anchor Family", "")).strip().zfill(4)[-4:]
        new_fams_text = str(row.get("New Family", "")).strip()

        for part in new_fams_text.replace(",", " / ").split("/"):
            nf = "".join(sorted(part.strip().zfill(4)[-4:]))
            if len(nf) == 4 and nf.isdigit():
                anchor_map[nf].add(anchor)

    rows = []
    for nf, anchors in anchor_map.items():
        support = len(anchors)
        if support >= min_support:
            rows.append({
                "No": nf,
                "Support": support,
                "Anchors": " / ".join(sorted(anchors)),
            })

    if not rows:
        return pd.DataFrame(), ""

    df = pd.DataFrame(rows).sort_values(
        ["Support", "No"],
        ascending=[False, True]
    ).head(top_n).reset_index(drop=True)

    grouped = []
    for support in sorted(df["Support"].unique(), reverse=True):
        nums = df[df["Support"] == support]["No"].astype(str).tolist()
        grouped.append(f"×{support}: " + " / ".join(nums))

    text = "🧬 Rumah A Predictor - Anchor Density Signal\n\n"
    text += "\n".join(grouped)

    return df, text


def build_pair_assist_pick_engine_v30(pair_assist_df, result_pairs, anchor_families=None, top_n=20):
    """
    Pair Assist Pick Engine.
    Pilih calon terbaik daripada output Pair Assist All Anchor.
    Ringkas dan tidak scan history.
    """
    import pandas as pd
    from collections import defaultdict

    if pair_assist_df is None or pair_assist_df.empty:
        return pd.DataFrame()

    result_pairs = [str(p).strip().zfill(2)[-2:] for p in (result_pairs or [])]
    result_pairs = list(dict.fromkeys([p for p in result_pairs if len(p) == 2 and p.isdigit()]))

    anchor_families = ["".join(sorted(str(f).strip().zfill(4)[-4:])) for f in (anchor_families or [])]
    anchor_families = list(dict.fromkeys([f for f in anchor_families if len(f) == 4]))

    score_map = defaultdict(float)
    from_map = defaultdict(list)
    anchor_count = defaultdict(set)
    pair_hit_map = defaultdict(set)

    # pair_assist_df format:
    # Anchor Family | New Family | Detail
    for _, row in pair_assist_df.iterrows():
        anchor = str(row.get("Anchor Family", "")).strip().zfill(4)[-4:]
        new_fams_text = str(row.get("New Family", "")).strip()
        detail_text = str(row.get("Detail", "")).strip()

        new_fams = []
        for part in new_fams_text.replace(",", " / ").split("/"):
            nf = "".join(sorted(part.strip().zfill(4)[-4:]))
            if len(nf) == 4 and nf.isdigit():
                new_fams.append(nf)

        for nf in new_fams:
            anchor_count[nf].add(anchor)

            # base score
            score_map[nf] += 5

            # muncul daripada banyak anchor family
            score_map[nf] += len(anchor_count[nf]) * 4

            # mengandungi pair result input
            for p in result_pairs:
                if p in nf or p[::-1] in nf:
                    score_map[nf] += 4
                    pair_hit_map[nf].add(p)

            # berkongsi 3 digit dengan mana-mana anchor family
            nf_set = set(nf)
            for af in anchor_families:
                if len(nf_set & set(af)) >= 3:
                    score_map[nf] += 3
                    break

            # bonus untuk hidden family yang ada double/pair kuat result 24/02/20/44
            for strong_pair in ["02", "20", "24", "42", "44", "08", "80"]:
                if strong_pair in result_pairs and (strong_pair in nf or strong_pair[::-1] in nf):
                    score_map[nf] += 3

            if detail_text:
                # simpan detail yang berkaitan family itu
                for d in detail_text.split(" / "):
                    if d.strip().endswith("-> " + nf) and d.strip() not in from_map[nf]:
                        from_map[nf].append(d.strip())

    rows = []
    for nf, score in score_map.items():
        rows.append({
            "No": nf,
            "Score": round(score, 2),
            "Anchor Count": len(anchor_count[nf]),
            "Pair Hit": " / ".join(sorted(pair_hit_map[nf])),
            "From Anchor": " / ".join(sorted(anchor_count[nf])),
            "Reason": " / ".join(from_map[nf][:8]),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values(
        ["Score", "Anchor Count", "No"],
        ascending=[False, False, True]
    ).head(top_n).reset_index(drop=True)

    return df



def build_pair_arrangement_engine_v30(pair_pick_df, result_pairs, top_per_family=3):
    import itertools
    import pandas as pd

    if pair_pick_df is None or pair_pick_df.empty:
        return pd.DataFrame()

    result_pairs = [str(p).zfill(2)[-2:] for p in (result_pairs or [])]
    rows = []

    for fam in pair_pick_df["No"].astype(str).tolist():
        fam = str(fam).zfill(4)[-4:]
        perms = sorted(set("".join(p) for p in itertools.permutations(fam, 4)))

        scored = []
        for p in perms:
            score = 0
            pairs = [p[0:2], p[1:3], p[2:4]]

            for rp in result_pairs:
                if rp in pairs:
                    score += 5
                elif rp[::-1] in pairs:
                    score += 4

            if p[0] in "890":
                score += 3
            elif p[0] in "024":
                score += 2

            if p[2:4] in result_pairs:
                score += 2

            scored.append((score, p))

        scored.sort(key=lambda x: (-x[0], x[1]))
        top3 = [x[1] for x in scored[:top_per_family]]

        rows.append({
            "Family": fam,
            "Top Arrangement": " / ".join(top3)
        })

    return pd.DataFrame(rows)


def build_selection_engine_v28(model_sources, family_df=None, pair_signal_df=None, dd_df=None, triple_df=None):
    """
    V28 Selection Engine.
    Lapisan pemilihan tambahan berdasarkan audit/backtest awal.
    Tidak mengubah AI Pick asal.

    Weight awal:
    - No Double: 40
    - Pasangan: 30
    - Peralihan: 20
    - Statistik: 10
    Pattern bonus:
    - Digit Family: +15
    - Pair Momentum: +10
    - Double-Double: +10
    - No Triple: +10
    """
    from collections import defaultdict

    model_weight = {
        "No Double": 40,
        "Pasangan": 30,
        "Peralihan": 20,
        "Statistik": 10,
    }

    rows = defaultdict(lambda: {
        "No": "",
        "Selection Score": 0,
        "Model Source": set(),
        "Pattern Support": set(),
        "Reason": [],
    })

    # Model score
    for source, nums in model_sources:
        weight = model_weight.get(source, 10)
        for rank, n in enumerate(nums, start=1):
            s = pad4(n)
            if not s:
                continue
            rows[s]["No"] = s

            if source not in rows[s]["Model Source"]:
                # rank bonus kecil supaya nombor atas model lebih dihargai
                rank_bonus = max(0, 11 - min(rank, 10))
                rows[s]["Selection Score"] += weight + rank_bonus
                rows[s]["Model Source"].add(source)
                rows[s]["Reason"].append(f"{source}+{weight}")

    # Digit Family bonus
    try:
        if family_df is not None and not family_df.empty and "Examples" in family_df.columns:
            for ex in family_df.head(20)["Examples"].astype(str).tolist():
                for raw in str(ex).replace(",", "/").split("/"):
                    s = pad4(raw.strip())
                    if s:
                        rows[s]["No"] = s
                        rows[s]["Selection Score"] += 15
                        rows[s]["Pattern Support"].add("Digit Family")
                        rows[s]["Reason"].append("Family+15")
    except Exception:
        pass

    # Pair Momentum bonus
    try:
        momentum_pairs = []
        if pair_signal_df is not None and not pair_signal_df.empty and "Pair" in pair_signal_df.columns:
            momentum_pairs = pair_signal_df.head(10)["Pair"].astype(str).tolist()

        for no, item in list(rows.items()):
            s = pad4(no)
            hit_pairs = []
            for p in momentum_pairs:
                if len(p) == 2 and p[0] in s and p[1] in s:
                    hit_pairs.append(p)
            if hit_pairs:
                item["Selection Score"] += 10
                item["Pattern Support"].add("Pair Momentum")
                item["Reason"].append("Pair+10")
    except Exception:
        pass

    # Double-Double bonus
    try:
        if dd_df is not None and not dd_df.empty and "No" in dd_df.columns:
            for n in dd_df["No"].astype(str).tolist():
                s = pad4(n)
                if s:
                    rows[s]["No"] = s
                    rows[s]["Selection Score"] += 10
                    rows[s]["Pattern Support"].add("Double-Double")
                    rows[s]["Reason"].append("DD+10")
    except Exception:
        pass

    # No Triple bonus
    try:
        if triple_df is not None and not triple_df.empty and "No" in triple_df.columns:
            for n in triple_df["No"].astype(str).tolist():
                s = pad4(n)
                if s:
                    rows[s]["No"] = s
                    rows[s]["Selection Score"] += 10
                    rows[s]["Pattern Support"].add("No Triple")
                    rows[s]["Reason"].append("Triple+10")
    except Exception:
        pass

    out = []
    for no, item in rows.items():
        score = int(item["Selection Score"])
        if score >= 80:
            status = "🔥 HIGH PRIORITY"
        elif score >= 60:
            status = "⭐ STRONG WATCH"
        elif score >= 45:
            status = "👀 WATCH"
        else:
            status = "LOW"

        out.append({
            "No": no,
            "Selection Score": score,
            "Status": status,
            "Model Source": ", ".join(sorted(item["Model Source"])) if item["Model Source"] else "-",
            "Pattern Support": ", ".join(sorted(item["Pattern Support"])) if item["Pattern Support"] else "-",
            "Reason": ", ".join(item["Reason"][:6]),
        })

    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.sort_values(["Selection Score", "No"], ascending=[False, True]).reset_index(drop=True)


def build_signal_strength_score(model_sources, family_df=None, pair_signal_df=None, dd_df=None, triple_df=None):
    """
    V27.2 Signal Strength Score v1.
    Lapisan analisis sahaja. Tidak ubah formula atau ranking asal.
    Scoring ringkas:
    - Nombor daripada model utama: +50
    - Muncul dalam lebih daripada satu model: +20 setiap model tambahan
    - Masuk Digit Family Rotation: +15
    - Mengandungi Pair Momentum: +10
    - Masuk Double-Double Watch: +10
    - Masuk No Triple Watch: +10
    """
    from collections import defaultdict

    score_map = defaultdict(lambda: {
        "No": "",
        "Score": 0,
        "Source": set(),
        "Pattern": set(),
    })

    # 1. Model source score
    for source, nums in model_sources:
        for n in nums:
            s = pad4(n)
            if not s:
                continue
            score_map[s]["No"] = s
            if source not in score_map[s]["Source"]:
                score_map[s]["Source"].add(source)
                score_map[s]["Score"] += 50 if len(score_map[s]["Source"]) == 1 else 20

    # 2. Digit Family Rotation score
    try:
        if family_df is not None and not family_df.empty and "Examples" in family_df.columns:
            for ex in family_df.head(20)["Examples"].astype(str).tolist():
                for raw in str(ex).replace(",", "/").split("/"):
                    s = pad4(raw.strip())
                    if s:
                        score_map[s]["No"] = s
                        score_map[s]["Score"] += 15
                        score_map[s]["Pattern"].add("Digit Family")
    except Exception:
        pass

    # 3. Pair Momentum score
    try:
        momentum_pairs = []
        if pair_signal_df is not None and not pair_signal_df.empty and "Pair" in pair_signal_df.columns:
            momentum_pairs = pair_signal_df.head(10)["Pair"].astype(str).tolist()

        for no, item in list(score_map.items()):
            s = pad4(no)
            hit_pairs = []
            for p in momentum_pairs:
                if len(p) == 2 and p[0] in s and p[1] in s:
                    hit_pairs.append(p)
            if hit_pairs:
                item["Score"] += 10
                item["Pattern"].add("Pair " + "/".join(hit_pairs[:3]))
    except Exception:
        pass

    # 4. Double-Double score
    try:
        if dd_df is not None and not dd_df.empty and "No" in dd_df.columns:
            for n in dd_df["No"].astype(str).tolist():
                s = pad4(n)
                if s:
                    score_map[s]["No"] = s
                    score_map[s]["Score"] += 10
                    score_map[s]["Pattern"].add("Double-Double")
    except Exception:
        pass

    # 5. No Triple score
    try:
        if triple_df is not None and not triple_df.empty and "No" in triple_df.columns:
            for n in triple_df["No"].astype(str).tolist():
                s = pad4(n)
                if s:
                    score_map[s]["No"] = s
                    score_map[s]["Score"] += 10
                    score_map[s]["Pattern"].add("No Triple")
    except Exception:
        pass

    rows = []
    for no, item in score_map.items():
        rows.append({
            "No": no,
            "Score": item["Score"],
            "Source": ", ".join(sorted(item["Source"])) if item["Source"] else "Pattern",
            "Pattern": ", ".join(sorted(item["Pattern"])) if item["Pattern"] else "-",
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Score", "No"], ascending=[False, True]).reset_index(drop=True)


def build_pattern_predictor(family_df, pair_signal_df, dd_df, triple_df):
    rows = []

    # Digit Family pattern
    try:
        if family_df is not None and not family_df.empty:
            top_family = family_df.iloc[0]
            rows.append({
                "Pattern": "Digit Family Rotation",
                "Signal": str(top_family.get("Strength", "")),
                "Watch": str(top_family.get("Examples", "")),
                "Status": "STRONG" if int(top_family.get("Signal", 0)) >= 3 else "WATCH",
            })
    except Exception:
        pass

    # Pair momentum
    try:
        if pair_signal_df is not None and not pair_signal_df.empty:
            top_pairs = pair_signal_df.head(5)["Pair"].astype(str).tolist()
            max_sig = int(pair_signal_df.iloc[0].get("Signal", 0))
            rows.append({
                "Pattern": "Pair Momentum",
                "Signal": "⭐" * min(max_sig, 5),
                "Watch": " / ".join(top_pairs),
                "Status": "STRONG" if max_sig >= 3 else "MEDIUM",
            })
    except Exception:
        pass

    # Double-double
    try:
        if dd_df is not None and not dd_df.empty:
            rows.append({
                "Pattern": "Double-Double Watch",
                "Signal": "⭐" * min(int(dd_df.iloc[0].get("Signal", 1)), 5),
                "Watch": " / ".join(dd_df.head(8)["No"].astype(str).tolist()),
                "Status": "WATCH",
            })
        else:
            rows.append({
                "Pattern": "Double-Double Watch",
                "Signal": "⭐",
                "Watch": "-",
                "Status": "LOW",
            })
    except Exception:
        pass

    # No triple
    try:
        if triple_df is not None and not triple_df.empty:
            rows.append({
                "Pattern": "No Triple Watch",
                "Signal": "⭐" * min(int(triple_df.iloc[0].get("Signal", 1)), 5),
                "Watch": " / ".join(triple_df.head(8)["No"].astype(str).tolist()),
                "Status": "WATCH",
            })
        else:
            rows.append({
                "Pattern": "No Triple Watch",
                "Signal": "⭐",
                "Watch": "-",
                "Status": "LOW",
            })
    except Exception:
        pass

    return pd.DataFrame(rows)


def get_no_list_for_signal(df, limit=20):
    try:
        if df is None or df.empty:
            return []
        return df["No"].astype(str).head(limit).tolist()
    except Exception:
        return []

def signal_digits_from_numbers(numbers):
    digits = set()
    for n in numbers:
        s = pad4(n)
        for d in s:
            digits.add(d)
    return digits

def signal_pairs_from_numbers(numbers):
    pairs = set()
    for n in numbers:
        s = pad4(n)
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                pairs.add(s[i] + s[j])
    return pairs

def build_signal_strength(stat_nums, position_nums, pair_nums, nodouble_nums):
    model_map = {
        "Statistik": stat_nums,
        "Peralihan": position_nums,
        "Pasangan": pair_nums,
        "No Double": nodouble_nums,
    }

    digit_rows = []
    pair_rows = []
    number_rows = []

    # Digit consensus
    for d in "0123456789":
        sources = []
        for model, nums in model_map.items():
            if d in signal_digits_from_numbers(nums):
                sources.append(model)
        if sources:
            digit_rows.append({
                "Digit": d,
                "Signal": len(sources),
                "Strength": "⭐" * len(sources),
                "Models": ", ".join(sources),
            })

    # Pair consensus
    all_pairs = set()
    model_pair_sets = {}
    for model, nums in model_map.items():
        pset = signal_pairs_from_numbers(nums)
        model_pair_sets[model] = pset
        all_pairs.update(pset)

    for p in sorted(all_pairs):
        sources = [m for m, pset in model_pair_sets.items() if p in pset]
        if len(sources) >= 2:
            pair_rows.append({
                "Pair": p,
                "Signal": len(sources),
                "Strength": "⭐" * len(sources),
                "Models": ", ".join(sources),
            })

    # Number consensus / model origin
    seen = {}
    for model, nums in model_map.items():
        for n in nums:
            s = pad4(n)
            if s not in seen:
                seen[s] = []
            if model not in seen[s]:
                seen[s].append(model)

    for n, sources in seen.items():
        number_rows.append({
            "No": n,
            "Signal": len(sources),
            "Strength": "⭐" * len(sources),
            "Models": ", ".join(sources),
        })

    digit_df = pd.DataFrame(digit_rows).sort_values(["Signal", "Digit"], ascending=[False, True])
    pair_df = pd.DataFrame(pair_rows).sort_values(["Signal", "Pair"], ascending=[False, True])
    number_df = pd.DataFrame(number_rows).sort_values(["Signal", "No"], ascending=[False, True])

    return digit_df, pair_df, number_df



@st.cache_data(show_spinner=False)
def load_latest_full_result_support():
    """
    V31 support signal sahaja:
    - Baca latest TotoFullResult.xlsx jika ada.
    - Digunakan untuk full-result digit/pair support.
    - Tidak menggantikan TotoHistoryAll dan tidak mengubah ranking chart.
    """
    try:
        import pandas as pd
        from pathlib import Path
        from collections import Counter

        fp = Path("TotoFullResult.xlsx")
        if not fp.exists():
            return {
                "nums": [],
                "digit_counts": Counter(),
                "pair_counts": Counter(),
                "top_digits": [],
                "top_pairs": [],
                "allow_triple_digits": set(),
            }

        df = pd.read_excel(fp)
        if df.empty:
            return {
                "nums": [],
                "digit_counts": Counter(),
                "pair_counts": Counter(),
                "top_digits": [],
                "top_pairs": [],
                "allow_triple_digits": set(),
            }

        if "DrawNo" in df.columns:
            df["_draw_sort"] = pd.to_numeric(df["DrawNo"], errors="coerce")
            latest = df.sort_values("_draw_sort").iloc[-1]
        else:
            latest = df.iloc[-1]

        nums = []
        for c in df.columns:
            if str(c) in ["DrawNo", "DrawDate", "_draw_sort"]:
                continue
            v = latest.get(c, "")
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass

            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue

            if "." in s:
                try:
                    s = str(int(float(s)))
                except Exception:
                    pass

            if s:
                nums.append(s.zfill(4)[-4:])

        digit_counts = Counter("".join(nums))
        pair_counts = Counter(get_pairs(nums))

        top_digits = [d for d, _ in sorted(digit_counts.items(), key=lambda x: (-x[1], x[0]))[:10]]
        top_pairs = [p for p, _ in sorted(pair_counts.items(), key=lambda x: (-x[1], x[0]))[:12]]

        # Triple dibenarkan hanya untuk digit yang jelas kuat.
        # Threshold dinamik: sekurang-kurangnya 8 hits atau Top 3 digit full result.
        allow_triple_digits = set()
        for d, cnt in sorted(digit_counts.items(), key=lambda x: (-x[1], x[0]))[:3]:
            if cnt >= 8:
                allow_triple_digits.add(d)

        return {
            "nums": nums,
            "digit_counts": digit_counts,
            "pair_counts": pair_counts,
            "top_digits": top_digits,
            "top_pairs": top_pairs,
            "allow_triple_digits": allow_triple_digits,
        }

    except Exception:
        from collections import Counter
        return {
            "nums": [],
            "digit_counts": Counter(),
            "pair_counts": Counter(),
            "top_digits": [],
            "top_pairs": [],
            "allow_triple_digits": set(),
        }


def generate(history, first, second, third):
    nums = [pad4(first), pad4(second), pad4(third)]
    audit_data = build_audit(history)

    # V31: Full result support signal sahaja.
    # Top 3 masih sumber utama, tetapi full result membantu digit/pair yang aktif.
    full_support = load_latest_full_result_support()

    present = set("".join(nums))
    full_present = set("".join(full_support.get("nums", [])))
    missing = [d for d in "0123456789" if d not in present]

    input_pairs = list(dict.fromkeys(get_pairs(nums)))

    # Pair score: Top3 pair utama + selected full-result pair sebagai support tambahan.
    current_pair_score = {p: audit_data["pair_rate"].get(p, 0) for p in input_pairs}


    top_pairs = top_keys(current_pair_score, 3)
    top_recent = top_keys(audit_data["recent100"], 10)

    # Campur full hot digits sebagai support, bukan ganti recent history.
    for d in full_support.get("top_digits", [])[:5]:
        if d not in top_recent:
            top_recent.append(d)
    top_recent = top_recent[:10]

    top_missing_next = top_keys(audit_data["missing_next"], 10)

    allow_triple_digits = set()

    # V31 position reference: guna 1st, 2nd, 3rd dengan weight.
    cur_refs = [(nums[0], 1.0), (nums[1], 0.35), (nums[2], 0.35)]

    pos_choice = []
    for pos in range(4):
        agg = Counter()
        for ref_no, w in cur_refs:
            trans = audit_data["pos_trans"][(pos, ref_no[pos])]
            for d, cnt in trans.items():
                agg[d] += cnt * w

        selected = [d for d, _ in agg.most_common(4)]
        if len(selected) < 4:
            for d in top_recent:
                if d not in selected:
                    selected.append(d)
                if len(selected) == 4:
                    break
        pos_choice.append(selected[:4])

    stat_cand, pos_cand, pair_cand, theory_cand, hybrid = (
        defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    )

    m1 = missing[0] if len(missing) >= 1 else top_recent[0]
    m2 = missing[1] if len(missing) >= 2 else top_recent[1]

    # V31: Model Statistik guna Top 5 pair, bukan pair pertama sahaja.
    if top_pairs:
        for prank, tp in enumerate(top_pairs[:5], start=1):
            pair_weight = 16 - prank
            for rd in top_recent[:5]:
                for mn in top_missing_next[:4]:
                    add_perm4(stat_cand, m1, rd, tp[0], mn, pair_weight, allow_triple_digits=allow_triple_digits)
                    add_perm4(stat_cand, m1, m2, rd, mn, pair_weight - 1, allow_triple_digits=allow_triple_digits)
                    add_perm4(stat_cand, m1, rd, tp[1], m2, pair_weight - 2, allow_triple_digits=allow_triple_digits)

    for x1, x2, x3, x4 in product(range(4), repeat=4):
        num = pos_choice[0][x1] + pos_choice[1][x2] + pos_choice[2][x3] + pos_choice[3][x4]
        sc = 20 - ((x1+1)+(x2+1)+(x3+1)+(x4+1))
        score_add(pos_cand, num, sc + num_position_score(num, audit_data, cur_refs), allow_triple_digits=allow_triple_digits)

    present_list = list(present)
    for rank, pr in enumerate(top_pairs[:9], start=1):
        for md in missing:
            for pdig in present_list:
                add_perm4(theory_cand, pr[0], pr[1], md, pdig, 12 + (10-rank), allow_triple_digits=allow_triple_digits)
                score_add(pair_cand, pr + md + pdig, 15 + (10-rank), allow_triple_digits=allow_triple_digits)
                score_add(pair_cand, pr + pdig + md, 13 + (10-rank), allow_triple_digits=allow_triple_digits)
            for rd in top_recent[:4]:
                score_add(pair_cand, pr + md + rd, 12 + (10-rank), allow_triple_digits=allow_triple_digits)
                score_add(pair_cand, pr + rd + md, 11 + (10-rank), allow_triple_digits=allow_triple_digits)

    for source in [stat_cand, pos_cand, pair_cand, theory_cand]:
        for num, base_score in source.items():
            sc = base_score
            sc += num_stat_score(num, audit_data, set(missing), present)
            sc += num_position_score(num, audit_data, cur_refs)
            sc += num_pair_score(num, audit_data, current_pair_score)
            score_add(hybrid, num, sc, allow_triple_digits=allow_triple_digits)

    audit_summary = {
        "missing": missing,
        "top_pairs": [(p, round(current_pair_score[p]*100, 2)) for p in top_pairs],
        "top_recent": top_recent[:10],
        "top_missing_next": top_missing_next[:10],
        "pos_choice": pos_choice,
        "v31_core_upgrade": {
            "full_result_support": bool(full_support.get("nums")),
            "full_top_digits": full_support.get("top_digits", [])[:5],
            "full_top_pairs": full_support.get("top_pairs", [])[:8],
            "allow_triple_digits": sorted(list(allow_triple_digits)),
            "position_refs": [n for n, _ in cur_refs],
        },
    }

    hybrid_all = add_confidence(make_table(hybrid, 100))
    return {
        "hybrid": hybrid_all.head(20).copy(),
        "hybrid_all": hybrid_all,
        "stat": add_confidence(make_table(stat_cand, 10)),
        "position": add_confidence(make_table(pos_cand, 10)),
        "pair": add_confidence(make_table(pair_cand, 10)),
        "theory": add_confidence(make_table(theory_cand, 20)),
        "audit": audit_summary,
    }

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
st.info(f"Status GitHub auto-save: {token_status}")
st.caption(f"Sumber data aktif: {history_source_label}")


# -----------------------------
# V14: History Manager Lengkap
# -----------------------------

st.subheader("📅 Keputusan Terbaru")
try:
    latest = st.session_state.history.iloc[-1]
    latest_draw = str(latest["draw_no"])
    latest_date = str(latest["draw_date"])
    latest_first = pad4(latest["first"])
    latest_second = pad4(latest["second"])
    latest_third = pad4(latest["third"])

    lc1, lc2 = st.columns(2)
    with lc1:
        st.metric("Draw No", latest_draw)
        st.caption(f"Tarikh: {latest_date}")
    with lc2:
        st.write(f"**1st:** {latest_first}")
        st.write(f"**2nd:** {latest_second}")
        st.write(f"**3rd:** {latest_third}")
except Exception:
    st.warning("Keputusan terbaru belum dapat dipaparkan.")

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


def family4(n):
    try:
        return "".join(sorted(pad4(n)))
    except Exception:
        return ""

def overlap_count_4d(a, b):
    from collections import Counter
    ca = Counter(pad4(a))
    cb = Counter(pad4(b))
    return sum((ca & cb).values())

def get_ranked_no_list_for_backtest(df, limit=15):
    try:
        if df is None or df.empty or "No" not in df.columns:
            return []
        x = df.copy()
        if "Rank" in x.columns:
            x["Rank"] = pd.to_numeric(x["Rank"], errors="coerce")
            x = x.sort_values("Rank", ascending=True)
        return [pad4(v) for v in x["No"].astype(str).head(limit).tolist()]
    except Exception:
        return []

def _split_family_text_to_list(text):
    out = []
    try:
        for part in str(text).replace(",", " / ").split("/"):
            s = "".join(sorted(part.strip().zfill(4)[-4:]))
            if len(s) == 4 and s.isdigit() and s not in out:
                out.append(s)
    except Exception:
        pass
    return out





def build_bridge_model_v31_9(first, second, third):
    import pandas as pd
    nums=[pad4(first),pad4(second),pad4(third)]
    existing_digits=sorted(set("".join(nums)))
    missing_digits=sorted(set("0123456789")-set(existing_digits))
    pair_rows=[]; base_pairs=[]
    family_meta={}
    bridge_order=[]

    for label,no in zip(["1st","2nd","3rd"],nums):
        for ptype,pair in zip(["Front","Middle","Back"],[no[:2],no[1:3],no[2:4]]):
            base_pairs.append(pair)
            pair_rows.append({"Source":label,"No":no,"Pair Type":ptype,"Pair":pair})

    base_pairs=list(dict.fromkeys(base_pairs))

    for row in pair_rows:
        pair=row["Pair"]
        src=row["Source"]
        ptype=row["Pair Type"]
        for md in missing_digits:
            for ed in existing_digits:
                # V31.21: ikut tertib pair asal.
                # Contoh 82 + 7 + 6 = 8276, bukan canonical 2678 untuk paparan.
                display_no = f"{pair}{md}{ed}"
                fam="".join(sorted(display_no))

                if len(fam)==4 and fam.isdigit():
                    if fam not in family_meta:
                        family_meta[fam]={
                            "Family":fam,
                            "Display No":display_no,
                            "Formula List":[],
                            "Base Pairs":set(),
                            "Sources":set(),
                            "Pair Types":set(),
                            "Missing Digits":set(),
                            "Existing Digits":set(),
                        }
                        bridge_order.append(fam)

                    formula=f"{pair}+{md}+{ed}"
                    family_meta[fam]["Formula List"].append(formula)
                    family_meta[fam]["Base Pairs"].add(pair)
                    family_meta[fam]["Sources"].add(src)
                    family_meta[fam]["Pair Types"].add(ptype)
                    family_meta[fam]["Missing Digits"].add(md)
                    family_meta[fam]["Existing Digits"].add(ed)

    rows=[]
    for order_idx, fam in enumerate(bridge_order, start=1):
        meta = family_meta[fam]
        rows.append({
            "No": meta["Display No"],
            "Family": fam,
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
    base_pairs = list(dict.fromkeys(base_pairs))

    family_meta = {}
    def add_candidate(pair, d1, d2, mode, source, pair_type):
        display_no = f"{pair}{d1}{d2}"
        fam = family4(display_no)
        meta = family_meta.setdefault(fam, {
            "No": display_no, "Family": fam, "Modes": set(), "Base Pairs": set(),
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
    for order, meta in enumerate(family_meta.values(), 1):
        rows.append({
            "No": meta["No"], "Family": meta["Family"], "Order": order,
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


@st.cache_data(show_spinner=False)
def build_bridge_v2_formula_reliability(history, lookback=800):
    """Walk-forward reliability bagi formula pair+2D V2 sahaja."""
    if history is None or history.empty or len(history) < 35:
        return {}
    h = history.copy().reset_index(drop=True)
    exposure, hits = Counter(), Counter()
    start = max(30, len(h) - int(lookback) - 1)
    for idx in range(start, len(h) - 1):
        try:
            src, nxt = h.iloc[idx], h.iloc[idx + 1]
            _, candidates, _ = build_bridge_engine_v2_pair_double_digit(src["first"], src["second"], src["third"])
            actual = {family4(nxt[c]) for c in ("first", "second", "third")}
            for _, row in candidates.iterrows():
                is_hit = family4(row["Family"]) in actual
                for formula in {x.strip() for x in str(row.get("Formula List", "")).split("/") if x.strip()}:
                    exposure[formula] += 1
                    if is_hit:
                        hits[formula] += 1
        except Exception:
            continue
    return {
        f: {"exposures": exposure[f], "hits": hits[f], "rate": (hits[f] + 1) / (exposure[f] + 25)}
        for f in exposure
    }


def build_bridge_v2_family_ranker(
    bridge_v2_df, bridge_v1_df=None, model_sources=None, anchor_df=None,
    density_df=None, formula_reliability=None, top_n=10,
):
    """Independent ranker untuk V2: conviction, balanced dan V2-unique coverage."""
    if bridge_v2_df is None or bridge_v2_df.empty:
        return pd.DataFrame(), ""
    model_sources = model_sources or []
    formula_reliability = formula_reliability or {}
    source_nums = {str(label): [pad4(x) for x in nums or []] for label, nums in model_sources}
    source_fams = {label: {family4(x) for x in nums} for label, nums in source_nums.items()}
    v1_fams = set(bridge_v1_df["Family"].astype(str).map(family4)) if bridge_v1_df is not None and not bridge_v1_df.empty else set()
    anchor_fams = set(anchor_df["Family"].astype(str).map(family4)) if anchor_df is not None and not anchor_df.empty and "Family" in anchor_df.columns else set()
    density_col = "Family" if density_df is not None and not density_df.empty and "Family" in density_df.columns else ("No" if density_df is not None and not density_df.empty and "No" in density_df.columns else None)
    density_fams = set(density_df[density_col].astype(str).map(family4)) if density_col else set()
    rows = []
    for _, row in bridge_v2_df.iterrows():
        fam = family4(row.get("Family", row.get("No", "")))
        formulas = {x.strip() for x in str(row.get("Formula List", "")).split("/") if x.strip()}
        rates = [float(formula_reliability.get(f, {}).get("rate", 0)) for f in formulas]
        history_rate = max(rates) if rates else 0
        genealogy = (
            int(row.get("Formula Support", 1)) * 6 + int(row.get("Source Support", 1)) * 5
            + int(row.get("Position Support", 1)) * 4 + int(row.get("Base Pair Support", 1)) * 4
        )
        mode = str(row.get("Mode", ""))
        mode_score = 7 if "2 Missing" in mode and "2 Existing" in mode else (4 if "2 Existing" in mode else 1)
        exact_models = [label for label, fams in source_fams.items() if fam in fams]
        overlap_models = [label for label, nums in source_nums.items() if label not in exact_models and any(overlap_count_4d(fam, n) >= 3 for n in nums)]
        model_score = len(exact_models) * 16 + min(len(overlap_models), 4) * 4
        v1_exact = fam in v1_fams
        v1_3d = (not v1_exact) and any(overlap_count_4d(fam, x) >= 3 for x in v1_fams)
        convergence = (24 if v1_exact else (6 if v1_3d else 0))
        convergence += 14 if fam in anchor_fams else (4 if any(overlap_count_4d(fam, x) >= 3 for x in anchor_fams) else 0)
        convergence += 14 if fam in density_fams else (4 if any(overlap_count_4d(fam, x) >= 3 for x in density_fams) else 0)
        score = round(genealogy + mode_score + model_score + convergence + history_rate * 1000, 2)
        reasons = [f"Genealogy {genealogy}", mode, f"History {history_rate:.3f}"]
        if v1_exact: reasons.append("V1 Exact")
        elif v1_3d: reasons.append("V1 3D")
        if exact_models: reasons.append("Exact: " + ", ".join(exact_models))
        if overlap_models: reasons.append("3D: " + ", ".join(overlap_models))
        rows.append({
            "No": pad4(row.get("No", fam)), "Family": fam, "V2 Score": score,
            "Mode": mode, "Genealogy": genealogy, "Formula History": round(history_rate, 4),
            "V1 Exact": v1_exact, "V1 3D": v1_3d, "V2 Unique": not v1_exact,
            "Base Pairs": str(row.get("Base Pairs", "")), "Exact Models": " / ".join(exact_models),
            "3D Models": " / ".join(overlap_models), "Reason": " | ".join(reasons),
        })
    df = pd.DataFrame(rows).sort_values(
        ["V2 Score", "Genealogy", "Formula History", "Family"], ascending=[False, False, False, True]
    ).drop_duplicates("Family").reset_index(drop=True)
    df["Conviction Rank"] = range(1, len(df) + 1)

    pair_order = []
    for value in bridge_v2_df["Base Pairs"].astype(str):
        for pair in [x.strip() for x in value.split("/") if x.strip()]:
            if pair not in pair_order: pair_order.append(pair)
    balanced_idx = []
    for pair in pair_order:
        eligible = df[df["Base Pairs"].apply(lambda x: pair in [p.strip() for p in str(x).split("/")])]
        if not eligible.empty and eligible.index[0] not in balanced_idx:
            balanced_idx.append(eligible.index[0])
        if len(balanced_idx) >= top_n: break
    for idx in df.index:
        if idx not in balanced_idx: balanced_idx.append(idx)
    balanced_map = {idx: rank for rank, idx in enumerate(balanced_idx, 1)}
    df["Balanced Rank"] = [balanced_map[i] for i in df.index]
    unique_view = df[df["V2 Unique"]].sort_values(["V2 Score", "Conviction Rank"], ascending=[False, True])
    unique_map = {idx: rank for rank, idx in enumerate(unique_view.index, 1)}
    df["Unique Rank"] = [unique_map.get(i, "") for i in df.index]

    text = "🧬 Rumah A Predictor - Bridge V2 Family Ranker\n\n"
    text += "Top 3 Conviction:\n" + " / ".join(df.head(3)["Family"].tolist()) + "\n\n"
    text += "Top 5 Conviction:\n" + " / ".join(df.head(5)["Family"].tolist()) + "\n\n"
    text += "Top 10 Balanced:\n" + " / ".join(df.sort_values("Balanced Rank").head(10)["Family"].tolist()) + "\n\n"
    text += "Top 10 V2 Unique Coverage:\n" + " / ".join(unique_view.head(10)["Family"].tolist())
    return df, text


def build_combined_family_ranker_v1_v2(v1_df, v2_df, top_n=10):
    """Reciprocal-rank fusion; tidak mencampurkan raw score V1 dan V2."""
    if (v1_df is None or v1_df.empty) and (v2_df is None or v2_df.empty):
        return pd.DataFrame(), ""
    v1_df = v1_df if v1_df is not None else pd.DataFrame()
    v2_df = v2_df if v2_df is not None else pd.DataFrame()
    def rank_map(df, rank_col):
        if df.empty or rank_col not in df.columns: return {}
        return {family4(row["Family"]): int(row[rank_col]) for _, row in df.iterrows() if str(row.get(rank_col, "")).isdigit()}
    v1_conv = rank_map(v1_df, "Conviction Rank"); v1_bal = rank_map(v1_df, "Balanced Rank")
    v2_conv = rank_map(v2_df, "Conviction Rank"); v2_bal = rank_map(v2_df, "Balanced Rank")
    families = sorted(set(v1_conv) | set(v2_conv))
    rows = []
    for fam in families:
        in_v1, in_v2 = fam in v1_conv, fam in v2_conv
        score = 0.0
        # Backtest-calibrated hierarchy: V2 ialah rank signal utama; V1 confirmation kecil.
        if in_v2: score += 100 / (10 + v2_conv[fam])
        if fam in v2_bal: score += 50 / (10 + v2_bal[fam])
        if in_v1: score += 20 / (10 + v1_conv[fam])
        if fam in v1_bal: score += 10 / (10 + v1_bal[fam])
        if in_v1 and in_v2: score += 4
        source = "V1 + V2" if in_v1 and in_v2 else ("V1 Only" if in_v1 else "V2 Only")
        reasons = [source]
        if in_v1: reasons.append(f"V1 C#{v1_conv[fam]}")
        if in_v2: reasons.append(f"V2 C#{v2_conv[fam]}")
        if fam in v1_bal: reasons.append(f"V1 B#{v1_bal[fam]}")
        if fam in v2_bal: reasons.append(f"V2 B#{v2_bal[fam]}")
        rows.append({
            "Family": fam, "Combined Score": round(score, 4), "Support": source,
            "V1 Conviction": v1_conv.get(fam, ""), "V2 Conviction": v2_conv.get(fam, ""),
            "V1 Balanced": v1_bal.get(fam, ""), "V2 Balanced": v2_bal.get(fam, ""),
            "Reason": " | ".join(reasons),
        })
    scored_df = pd.DataFrame(rows).sort_values(
        ["Combined Score", "Support", "Family"], ascending=[False, True, True]
    ).reset_index(drop=True)
    # Validated fusion: V2 menentukan shortlist kerana liputannya lebih kuat.
    # V1 kekal sebagai confirmation/tie-break signal; tiada slot V1 dipaksa
    # kerana audit 100 draw menunjukkan paksaan itu menurunkan hit Top 10.
    v2_primary = []
    if not v2_df.empty:
        if "Unique Rank" in v2_df.columns:
            u = v2_df[pd.to_numeric(v2_df["Unique Rank"], errors="coerce").notna()].copy()
            u["_ur"] = pd.to_numeric(u["Unique Rank"], errors="coerce")
            v2_primary = u.sort_values("_ur")["Family"].astype(str).map(family4).tolist()
        if not v2_primary:
            v2_primary = v2_df.sort_values("Conviction Rank")["Family"].astype(str).map(family4).tolist()
    portfolio = []
    vi = 0
    for slot in range(1, int(top_n) + 1):
        pool = v2_primary
        idx = vi
        while idx < len(pool) and pool[idx] in portfolio: idx += 1
        if idx < len(pool):
            portfolio.append(pool[idx]); idx += 1
        vi = idx
    for fam in scored_df["Family"].tolist():
        if fam not in portfolio: portfolio.append(fam)
    order_map = {fam: i for i, fam in enumerate(portfolio)}
    df = scored_df.sort_values("Family", key=lambda s: s.map(order_map)).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    text = "🏆 Rumah A Predictor - Combined Family Ranker V1 + V2\n\n"
    for cutoff in (3, 5, 10):
        text += f"Top {cutoff}:\n" + " / ".join(df.head(cutoff)["Family"].tolist()) + "\n\n"
    return df, text.strip()


def build_bridge_family_ranker_v31_24(
    bridge_df,
    model_sources=None,
    ai_nums=None,
    anchor_df=None,
    density_df=None,
    full_support=None,
    formula_reliability=None,
    top_n=10,
):
    """
    Bridge Family Ranker V1.

    Bridge kekal sebagai coverage engine. Ranker memilih family berdasarkan:
    1) genealogy/support dalaman Bridge,
    2) consensus family dan overlap 3D daripada model lain,
    3) Anchor/Density,
    4) konteks digit/pair keputusan penuh terkini.

    Semua perbandingan dibuat pada canonical family, bukan arrangement.
    """
    if bridge_df is None or bridge_df.empty or "Family" not in bridge_df.columns:
        return pd.DataFrame(), ""

    model_sources = model_sources or []
    ai_nums = [pad4(x) for x in (ai_nums or []) if str(x).strip()]
    full_support = full_support or {}
    formula_reliability = formula_reliability or {}

    source_family_sets = {}
    source_numbers = {}
    for label, nums in model_sources:
        clean = [pad4(x) for x in (nums or []) if str(x).strip()]
        source_numbers[str(label)] = clean
        source_family_sets[str(label)] = {family4(x) for x in clean}
    if ai_nums:
        source_numbers["AI/Champion"] = ai_nums
        source_family_sets["AI/Champion"] = {family4(x) for x in ai_nums}

    anchor_fams = set()
    if anchor_df is not None and not anchor_df.empty and "Family" in anchor_df.columns:
        anchor_fams = {family4(x) for x in anchor_df["Family"].astype(str).tolist()}

    density_fams = set()
    if density_df is not None and not density_df.empty:
        density_col = "Family" if "Family" in density_df.columns else ("No" if "No" in density_df.columns else None)
        if density_col:
            density_fams = {family4(x) for x in density_df[density_col].astype(str).tolist()}

    digit_counts = full_support.get("digit_counts", Counter())
    pair_counts = full_support.get("pair_counts", Counter())
    max_digit = max(digit_counts.values()) if digit_counts else 1
    max_pair = max(pair_counts.values()) if pair_counts else 1

    rows = []
    for _, r in bridge_df.iterrows():
        family = family4(r.get("Family", r.get("No", "")))
        display_no = pad4(r.get("No", family))
        if len(family) != 4:
            continue

        formula_support = int(pd.to_numeric(r.get("Formula Support", 1), errors="coerce") or 1)
        source_support = int(pd.to_numeric(r.get("Source Support", 1), errors="coerce") or 1)
        position_support = int(pd.to_numeric(r.get("Position Support", 1), errors="coerce") or 1)
        pair_support = int(pd.to_numeric(r.get("Base Pair Support", 1), errors="coerce") or 1)
        genealogy_score = formula_support * 8 + source_support * 5 + position_support * 4 + pair_support * 4
        formulas = [x.strip() for x in str(r.get("Formula List", "")).split("/") if x.strip()]
        formula_rates = [float(formula_reliability.get(x, {}).get("rate", 0)) for x in formulas]
        historical_formula_rate = max(formula_rates) if formula_rates else 0
        historical_formula_score = round(historical_formula_rate * 1000, 2)

        exact_sources = []
        overlap_sources = []
        for label, fams in source_family_sets.items():
            if family in fams:
                exact_sources.append(label)
            elif any(overlap_count_4d(family, n) >= 3 for n in source_numbers.get(label, [])):
                overlap_sources.append(label)

        consensus_score = len(exact_sources) * 18 + min(len(overlap_sources), 4) * 4
        anchor_exact = family in anchor_fams
        anchor_overlap = (not anchor_exact) and any(overlap_count_4d(family, x) >= 3 for x in anchor_fams)
        density_exact = family in density_fams
        density_overlap = (not density_exact) and any(overlap_count_4d(family, x) >= 3 for x in density_fams)
        convergence_score = (22 if anchor_exact else (6 if anchor_overlap else 0)) + (22 if density_exact else (6 if density_overlap else 0))

        digits = list(family)
        fam_pairs = {"".join(sorted(digits[i] + digits[j])) for i in range(4) for j in range(i + 1, 4)}
        full_digit_score = round(sum(digit_counts.get(d, 0) for d in digits) / (4 * max_digit) * 8, 2)
        full_pair_score = round(sum(pair_counts.get(p, 0) for p in fam_pairs) / (max(1, len(fam_pairs)) * max_pair) * 8, 2)
        full_score = full_digit_score + full_pair_score

        structure = "-".join(map(str, sorted(Counter(family).values(), reverse=True)))
        structure_score = 3 if structure == "1-1-1-1" else 1
        total_score = round(genealogy_score + consensus_score + convergence_score + full_score + structure_score + historical_formula_score, 2)

        reasons = [f"Genealogy {genealogy_score}"]
        if historical_formula_rate:
            reasons.append(f"Formula History {historical_formula_rate:.3f}")
        if exact_sources:
            reasons.append("Exact: " + ", ".join(exact_sources))
        if overlap_sources:
            reasons.append("3D: " + ", ".join(overlap_sources[:4]))
        if anchor_exact or anchor_overlap:
            reasons.append("Anchor " + ("Exact" if anchor_exact else "3D"))
        if density_exact or density_overlap:
            reasons.append("Density " + ("Exact" if density_exact else "3D"))
        reasons.append(f"Full {round(full_score, 1)}")

        rows.append({
            "No": display_no,
            "Family": family,
            "Family Score": total_score,
            "Genealogy": genealogy_score,
            "Consensus": consensus_score,
            "Convergence": convergence_score,
            "Full Result": round(full_score, 2),
            "Formula History": round(historical_formula_rate, 4),
            "Base Pairs": str(r.get("Base Pairs", "")),
            "Exact Models": " / ".join(exact_sources),
            "3D Models": " / ".join(overlap_sources),
            "Reason": " | ".join(reasons),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df, ""
    df = df.sort_values(
        ["Family Score", "Consensus", "Convergence", "Genealogy", "Full Result", "Family"],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)
    df["Conviction Rank"] = range(1, len(df) + 1)

    # Balanced shortlist: ambil wakil terbaik daripada setiap base pair dahulu.
    # Ini mengelakkan satu pair dominan memenuhi semua slot Top 10.
    pair_order = []
    for value in bridge_df.get("Base Pairs", pd.Series(dtype=str)).astype(str).tolist():
        for pair in [x.strip() for x in value.split("/") if x.strip()]:
            if pair not in pair_order:
                pair_order.append(pair)
    balanced_indices = []
    for pair in pair_order:
        eligible = df[df["Base Pairs"].astype(str).apply(lambda x: pair in [p.strip() for p in x.split("/")])]
        if not eligible.empty:
            # Dalam kumpulan pair, formula history menjadi pemecah seri utama.
            pick = eligible.sort_values(
                ["Formula History", "Family Score", "Conviction Rank"],
                ascending=[False, False, True],
            ).index[0]
            if pick not in balanced_indices:
                balanced_indices.append(pick)
        if len(balanced_indices) >= top_n:
            break
    for idx in df.index:
        if idx not in balanced_indices:
            balanced_indices.append(idx)
        if len(balanced_indices) >= top_n:
            break
    balanced_rank_map = {idx: rank for rank, idx in enumerate(balanced_indices, start=1)}
    next_rank = len(balanced_rank_map) + 1
    for idx in df.index:
        if idx not in balanced_rank_map:
            balanced_rank_map[idx] = next_rank
            next_rank += 1
    df["Balanced Rank"] = [balanced_rank_map[idx] for idx in df.index]
    df = df[["Conviction Rank", "Balanced Rank", "No", "Family", "Family Score", "Genealogy", "Formula History", "Consensus", "Convergence", "Full Result", "Base Pairs", "Exact Models", "3D Models", "Reason"]]

    conviction_top = df.sort_values("Conviction Rank").head(top_n)
    balanced_top = df.sort_values("Balanced Rank").head(top_n)
    text = "🧬 Rumah A Predictor - Bridge Family Ranker V1\n\n"
    for cutoff in (3, 5):
        vals = conviction_top.head(cutoff)["Family"].astype(str).tolist()
        text += f"Top {cutoff} Conviction:\n" + " / ".join(vals) + "\n\n"
    balanced_vals = balanced_top.head(10)["Family"].astype(str).tolist()
    text += "Top 10 Balanced:\n" + " / ".join(balanced_vals) + "\n"
    return df, text.strip()


@st.cache_data(show_spinner=False)
def build_bridge_formula_reliability_v31_24(history, lookback=1500):
    """Walk-forward formula genealogy daripada draw lama sahaja."""
    if history is None or history.empty or len(history) < 40:
        return {}
    h = history.copy().reset_index(drop=True)
    start = max(30, len(h) - int(lookback))
    exposures = Counter()
    hits = Counter()
    for idx in range(start, len(h) - 1):
        try:
            source = h.iloc[idx]
            actual = h.iloc[idx + 1]
            _, bridge_hist, _ = build_bridge_model_v31_9(source["first"], source["second"], source["third"])
            actual_fams = {family4(actual["first"]), family4(actual["second"]), family4(actual["third"])}
            for _, row in bridge_hist.iterrows():
                is_hit = family4(row.get("Family", "")) in actual_fams
                formulas = {x.strip() for x in str(row.get("Formula List", "")).split("/") if x.strip()}
                for formula in formulas:
                    exposures[formula] += 1
                    if is_hit:
                        hits[formula] += 1
        except Exception:
            continue
    return {
        formula: {
            "exposures": exposures[formula],
            "hits": hits[formula],
            "rate": (hits[formula] + 1) / (exposures[formula] + 25),
        }
        for formula in exposures
    }


def rerank_bridge_v1_corrected_v31_26(ranker_df, profile="corrected", top_n=10):
    """Audit-safe V1 reranker. Hanya guna komponen yang tersedia pada source draw."""
    if ranker_df is None or ranker_df.empty:
        return pd.DataFrame()
    df = ranker_df.copy()
    for col in ("Genealogy", "Consensus", "Convergence", "Full Result"):
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0.0)
    if profile == "genealogy":
        df["Corrected Score"] = df["Genealogy"]
    elif profile == "genealogy_consensus":
        df["Corrected Score"] = df["Genealogy"] + df["Consensus"]
    elif profile == "genealogy_convergence":
        df["Corrected Score"] = df["Genealogy"] + df["Convergence"]
    else:
        # Empat model lama hanya confirmation kecil. Formula History dan Full
        # Result dikeluarkan sehingga ada walk-forward evidence yang sah.
        df["Corrected Score"] = (
            df["Genealogy"] + 0.25 * df["Consensus"] + df["Convergence"]
        )
    df = df.sort_values(
        ["Corrected Score", "Genealogy", "Convergence", "Consensus", "Family"],
        ascending=[False, False, False, False, True],
    ).reset_index(drop=True)
    df["Corrected Rank"] = range(1, len(df) + 1)

    # Diversity Top 10: wakil terbaik setiap base pair, kemudian isi ikut skor.
    pair_order = []
    for value in df.get("Base Pairs", pd.Series(dtype=str)).astype(str):
        for pair in [x.strip() for x in value.split("/") if x.strip()]:
            if pair not in pair_order:
                pair_order.append(pair)
    selected = []
    for pair in pair_order:
        eligible = df[df["Base Pairs"].astype(str).apply(
            lambda x: pair in [p.strip() for p in x.split("/")]
        )]
        if not eligible.empty:
            idx = eligible.index[0]
            if idx not in selected:
                selected.append(idx)
        if len(selected) >= int(top_n):
            break
    for idx in df.index:
        if idx not in selected:
            selected.append(idx)
        if len(selected) >= int(top_n):
            break
    balanced_map = {idx: rank for rank, idx in enumerate(selected, 1)}
    next_rank = len(balanced_map) + 1
    for idx in df.index:
        if idx not in balanced_map:
            balanced_map[idx] = next_rank
            next_rank += 1
    df["Corrected Balanced Rank"] = [balanced_map[idx] for idx in df.index]
    df["Corrected Profile"] = profile
    return df


def promote_v1_genealogy_corrected_v31_26(ranker_df, top_n=10):
    """Jadikan keputusan audit terbaik (Genealogy direct) sebagai kontrak V1."""
    df = rerank_bridge_v1_corrected_v31_26(ranker_df, profile="genealogy", top_n=top_n)
    if df.empty:
        return df
    df = df.drop(columns=["Conviction Rank", "Balanced Rank"], errors="ignore")
    df = df.rename(columns={"Corrected Rank": "Conviction Rank"})
    # Audit membuktikan direct Top 10 (6 hit) mengatasi forced-balanced (5 hit).
    df["Balanced Rank"] = df["Conviction Rank"]
    return df


def build_bridge_selection_engine_v31_10(bridge_df, top_n=60):
    """
    Bridge Selection Engine V1.
    Rank semua Bridge family berdasarkan support dalaman sahaja.
    Tidak guna DDE, AI atau result masa depan.

    Score:
    - Formula Support x4
    - Source Support x3
    - Position Support x3
    - Base Pair Support x2

    Output utama boleh dipotong Top N untuk backend threshold.
    """
    import pandas as pd
    if bridge_df is None or bridge_df.empty or "Family" not in bridge_df.columns:
        return pd.DataFrame(), ""

    df=bridge_df.copy()
    for col in ["Formula Support","Source Support","Position Support","Base Pair Support"]:
        if col not in df.columns:
            df[col]=1
        df[col]=pd.to_numeric(df[col], errors="coerce").fillna(1).astype(int)

    df["Bridge Score"]=(
        df["Formula Support"]*4+
        df["Source Support"]*3+
        df["Position Support"]*3+
        df["Base Pair Support"]*2
    )

    df["Reason"]=(
        "Formula "+df["Formula Support"].astype(str)+
        " | Source "+df["Source Support"].astype(str)+
        " | Position "+df["Position Support"].astype(str)+
        " | Pair "+df["Base Pair Support"].astype(str)
    )

    if "No" not in df.columns:
        df["No"] = df["Family"]
    df=df.sort_values(
        ["Bridge Score","Formula Support","Source Support","Position Support","Order"],
        ascending=[False,False,False,False,True]
    ).reset_index(drop=True)
    df["Rank"]=range(1,len(df)+1)

    top=df.head(top_n)["No"].astype(str).tolist()

    text="🧩 Rumah A Predictor - Bridge Selection Engine V1\n\n"
    text+=f"🔥 Top {top_n}:\n"
    for i in range(0,len(top),10):
        text+=" / ".join(top[i:i+10])+"\n"
    text+="\n📊 Detail:\n"
    for _,r in df.head(top_n).iterrows():
        text+=f"{r['Rank']}. {r['No']} - Score {r['Bridge Score']} ({r['Reason']})\n"

    return df, text



# -----------------------------
# V31.21: Bridge Selection Engine V2 audit weights
# Derived from Bridge formula audit backend.
# -----------------------------
BRIDGE_V2_PAIR_SCORE = {'02': 2, '03': 2, '06': 2, '07': 1, '10': 1, '12': 1, '13': 3, '14': 2, '15': 4, '16': 1, '17': 2, '20': 1, '21': 3, '22': 1, '24': 4, '25': 1, '26': 1, '31': 2, '32': 1, '35': 1, '39': 1, '41': 2, '42': 2, '43': 1, '45': 2, '47': 2, '48': 2, '49': 1, '51': 5, '52': 1, '53': 1, '54': 1, '55': 3, '56': 2, '57': 2, '58': 2, '61': 4, '62': 1, '63': 2, '64': 1, '65': 1, '66': 1, '67': 2, '68': 1, '69': 1, '71': 1, '72': 2, '73': 1, '75': 3, '76': 1, '79': 1, '81': 1, '82': 1, '83': 2, '85': 2, '86': 1, '87': 2, '89': 1, '90': 1, '94': 2, '95': 1, '96': 2}
BRIDGE_V2_SOURCE_POSITION_SCORE = {'1st Back': 9, '1st Front': 14, '1st Middle': 18, '2nd Back': 12, '2nd Front': 5, '2nd Middle': 10, '3rd Back': 16, '3rd Front': 14, '3rd Middle': 7}
BRIDGE_V2_MISSING_SCORE = {'0': 4, '1': 13, '2': 5, '3': 14, '4': 9, '5': 7, '6': 13, '7': 7, '8': 16, '9': 17}
BRIDGE_V2_EXISTING_SCORE = {'0': 12, '1': 9, '2': 7, '3': 8, '4': 12, '5': 12, '6': 17, '7': 12, '8': 6, '9': 10}
BRIDGE_V2_FORMULA_SCORE = {'02+4+6': 1, '02+9+0': 1, '03+7+1': 1, '03+8+5': 1, '06+1+2': 1, '06+3+9': 1, '07+1+4': 1, '10+3+2': 1, '12+3+0': 1, '13+6+4': 1, '13+9+5': 1, '13+9+6': 1, '14+8+6': 1, '14+9+1': 1, '15+3+6': 1, '15+3+8': 1, '15+4+0': 2, '16+9+3': 1, '17+0+5': 1, '17+8+6': 1, '20+9+0': 1, '21+3+6': 1, '21+5+6': 1, '21+7+4': 1, '22+3+8': 1, '24+1+9': 1, '24+5+0': 1, '24+5+7': 1, '24+6+8': 1, '25+9+6': 1, '26+1+4': 1, '31+7+0': 1, '31+7+3': 1, '32+4+9': 1, '35+9+4': 1, '39+1+9': 1, '41+6+3': 1, '41+9+1': 1, '42+6+7': 1, '42+6+8': 1, '43+9+5': 1, '45+1+2': 1, '45+6+5': 1, '47+5+6': 1, '47+6+2': 1, '48+6+2': 1, '48+9+5': 1, '49+7+0': 1, '51+0+7': 1, '51+4+0': 1, '51+4+9': 2, '51+8+7': 1, '52+6+0': 1, '53+9+1': 1, '54+9+8': 1, '55+1+7': 2, '55+6+4': 1, '56+2+6': 1, '56+9+1': 1, '57+4+5': 1, '57+6+0': 1, '58+0+8': 1, '58+2+1': 1, '61+0+2': 1, '61+8+6': 1, '61+8+7': 1, '61+9+5': 1, '62+5+1': 1, '63+8+7': 1, '63+8+9': 1, '64+3+4': 1, '65+2+6': 1, '66+7+9': 1, '67+3+9': 1, '67+8+3': 1, '68+1+5': 1, '69+3+7': 1, '71+8+6': 1, '72+3+0': 1, '72+6+4': 1, '73+8+6': 1, '75+1+5': 1, '75+6+1': 1, '75+8+1': 1, '76+8+3': 1, '79+8+4': 1, '81+2+5': 1, '82+3+6': 1, '83+5+3': 2, '85+1+6': 1, '85+9+4': 1, '86+2+4': 1, '87+4+7': 1, '87+9+5': 1, '89+7+9': 1, '90+3+6': 1, '94+1+2': 1, '94+8+7': 1, '95+1+4': 1, '96+3+7': 1, '96+8+3': 1}


def build_bridge_selection_engine_v31_11(bridge_df, top_n=60):
    """
    Bridge Selection Engine V2.
    Berdasarkan audit formula sebenar:
    Pair Score + Source Position Score + Missing Score + Existing Score + Formula Support.

    Tidak guna DDE/AI/result masa depan untuk draw semasa.
    Weight datang daripada audit backend sejarah.
    """
    import pandas as pd

    if bridge_df is None or bridge_df.empty or "Family" not in bridge_df.columns:
        return pd.DataFrame(), ""

    rows = []

    for _, r in bridge_df.iterrows():
        fam = pad4(r.get("Family", ""))

        formula_list = []
        if "Formula List" in bridge_df.columns:
            formula_list = [x.strip() for x in str(r.get("Formula List", "")).split("/") if x.strip()]
        elif "Formula" in bridge_df.columns:
            formula_list = [str(r.get("Formula", "")).strip()]

        pair_score = 0
        missing_score = 0
        existing_score = 0
        formula_score = 0

        # Source-position score guna metadata family jika ada.
        source_position_score = 0
        sources = [x.strip() for x in str(r.get("Sources", "")).split("/") if x.strip()]
        ptypes = [x.strip() for x in str(r.get("Pair Types", "")).split("/") if x.strip()]
        for s in sources:
            for p in ptypes:
                source_position_score += BRIDGE_V2_SOURCE_POSITION_SCORE.get(f"{s} {p}", 0)

        # Formula-based scores.
        for f in formula_list:
            parts = f.split("+")
            if len(parts) == 3:
                pair, md, ed = parts[0].strip(), parts[1].strip(), parts[2].strip()
                pair_score += BRIDGE_V2_PAIR_SCORE.get(pair, 0)
                missing_score += BRIDGE_V2_MISSING_SCORE.get(md, 0)
                existing_score += BRIDGE_V2_EXISTING_SCORE.get(ed, 0)
                formula_score += BRIDGE_V2_FORMULA_SCORE.get(f, 0)

        try:
            formula_support = int(r.get("Formula Support", len(formula_list)))
        except Exception:
            formula_support = len(formula_list)

        # Balance / anti-aggressive:
        # Pair & source-position penting, tapi missing/existing juga diberi ruang.
        total_score = (
            pair_score * 4
            + source_position_score * 2
            + missing_score * 2
            + existing_score * 2
            + formula_score * 5
            + formula_support
        )

        rows.append({
            "No": r.get("No", fam),
            "Family": fam,
            "Bridge V2 Score": total_score,
            "Pair Score": pair_score,
            "Source Position Score": source_position_score,
            "Missing Score": missing_score,
            "Existing Score": existing_score,
            "Formula Hit Score": formula_score,
            "Formula Support": formula_support,
            "Base Pairs": r.get("Base Pairs", ""),
            "Sources": r.get("Sources", ""),
            "Pair Types": r.get("Pair Types", ""),
            "Formula List": r.get("Formula List", ""),
            "Reason": f"Pair {pair_score} | SP {source_position_score} | M {missing_score} | E {existing_score} | F {formula_score} | Sup {formula_support}",
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(), ""

    if "Order" not in df.columns:
        df["Order"] = range(1, len(df)+1)
    df = df.sort_values(
        ["Bridge V2 Score", "Pair Score", "Source Position Score", "Formula Support", "Order"],
        ascending=[False, False, False, False, True]
    ).reset_index(drop=True)

    df["Rank"] = range(1, len(df) + 1)

    top = df.head(top_n)["No"].astype(str).tolist()

    text = "🧩 Rumah A Predictor - Bridge Selection Engine V2\n\n"
    text += f"🔥 Top {top_n}:\n"
    for i in range(0, len(top), 10):
        text += " / ".join(top[i:i+10]) + "\n"

    text += "\n📊 Detail:\n"
    for _, rr in df.head(top_n).iterrows():
        text += f"{rr['Rank']}. {rr['No']} - Score {rr['Bridge V2 Score']} ({rr['Reason']})\n"

    return df, text



# -----------------------------
# V31.21: Bridge Selection Engine V3 weights
# Pair Slot + Coverage + Slot Relationship + Formula.
# -----------------------------
BRIDGE_V3_SLOT_SCORE = {1: 16, 2: 20, 3: 9, 4: 5, 5: 11, 6: 13, 7: 14, 8: 7, 9: 17}
BRIDGE_V3_RELATION_SCORE = {'1+2': 7, '1+5': 2, '1+6': 2, '1+7': 1, '1+8': 1, '1+9': 4, '2+3': 2, '2+5': 1, '2+6': 4, '2+7': 2, '2+8': 1, '2+9': 4, '3+7': 1, '4+5': 1, '4+7': 1, '5+6': 2, '5+7': 1, '5+9': 1, '6+7': 2, '6+8': 2, '6+9': 3, '7+8': 3, '7+9': 2, '8+9': 3}
BRIDGE_V3_FORMULA_SCORE = {'02+4+6': 1, '02+9+0': 1, '03+7+1': 1, '03+8+5': 1, '06+1+2': 1, '06+3+9': 1, '07+1+4': 1, '10+3+2': 1, '12+3+0': 1, '13+6+4': 1, '13+9+5': 1, '13+9+6': 1, '14+8+6': 1, '14+9+1': 1, '15+3+6': 1, '15+3+8': 1, '15+4+0': 2, '16+9+3': 1, '17+0+5': 1, '17+8+6': 1, '20+9+0': 1, '21+3+6': 1, '21+5+6': 1, '21+7+4': 1, '22+3+8': 1, '24+1+9': 1, '24+5+0': 1, '24+5+7': 1, '24+6+8': 1, '25+9+6': 1, '26+1+4': 1, '26+7+8': 1, '31+7+0': 1, '31+7+3': 1, '32+4+9': 1, '35+9+4': 1, '39+1+9': 1, '41+6+3': 1, '41+9+1': 1, '42+6+7': 1, '42+6+8': 1, '43+9+5': 1, '45+1+2': 1, '45+6+5': 1, '47+5+6': 1, '47+6+2': 1, '48+6+2': 1, '48+9+5': 1, '49+7+0': 1, '51+0+7': 1, '51+4+0': 1, '51+4+9': 2, '51+8+7': 1, '52+6+0': 1, '53+9+1': 1, '54+9+8': 1, '55+1+7': 2, '55+6+4': 1, '56+2+6': 1, '56+9+1': 1, '57+4+5': 1, '57+6+0': 1, '58+0+8': 1, '58+2+1': 1, '58+7+9': 1, '61+0+2': 1, '61+8+6': 1, '61+8+7': 1, '61+9+5': 1, '62+5+1': 1, '63+8+7': 1, '63+8+9': 1, '64+3+4': 1, '65+2+6': 1, '66+7+9': 1, '67+3+9': 1, '67+8+3': 1, '68+1+5': 1, '68+4+8': 1, '68+7+2': 1, '69+3+7': 1, '71+8+6': 1, '72+3+0': 1, '72+6+4': 1, '73+8+6': 1, '75+1+5': 1, '75+6+1': 1, '75+8+1': 1, '76+8+3': 1, '79+8+4': 1, '81+2+5': 1, '82+3+6': 1, '82+7+6': 1, '83+5+3': 2, '85+1+6': 1, '85+9+4': 1, '86+2+4': 1, '86+4+8': 1, '86+7+2': 1, '87+4+7': 1, '87+9+5': 1, '89+7+9': 1, '90+3+6': 1, '94+1+2': 1, '94+8+7': 1, '95+1+4': 1, '96+3+7': 1, '96+8+3': 1}
BRIDGE_V3_COVERAGE_SCORE = {1: 40, 2: 23, 3: 6, 4: 2}

def build_bridge_selection_engine_v31_12(bridge_df, top_n=60):
    import pandas as pd
    if bridge_df is None or bridge_df.empty or "Family" not in bridge_df.columns:
        return pd.DataFrame(), ""

    rows=[]
    for _,r in bridge_df.iterrows():
        fam=pad4(r.get("Family",""))
        formulas=[x.strip() for x in str(r.get("Formula List","")).split("/") if x.strip()]
        slot_set=set()
        rel_score=0
        slot_score=0
        formula_score=0

        # Reconstruct slot from formula by matching formula pair against source slot metadata
        # bridge_df stores Formula List only, but Base Pairs/Sources/Pair Types summary also exists.
        # Use pair occurrence order from formula list; approximate slot score with all known source-position summaries.
        srcs=[x.strip() for x in str(r.get("Sources","")).split("/") if x.strip()]
        ptypes=[x.strip() for x in str(r.get("Pair Types","")).split("/") if x.strip()]
        source_slot_map={
            ("1st","Front"):1, ("1st","Middle"):2, ("1st","Back"):3,
            ("2nd","Front"):4, ("2nd","Middle"):5, ("2nd","Back"):6,
            ("3rd","Front"):7, ("3rd","Middle"):8, ("3rd","Back"):9,
        }
        for s in srcs:
            for p in ptypes:
                if (s,p) in source_slot_map:
                    slot_set.add(source_slot_map[(s,p)])

        for s in slot_set:
            slot_score += BRIDGE_V3_SLOT_SCORE.get(s,0)

        slot_list=sorted(slot_set)
        for i in range(len(slot_list)):
            for j in range(i+1,len(slot_list)):
                rel_score += BRIDGE_V3_RELATION_SCORE.get(f"{slot_list[i]}+{slot_list[j]}",0)

        for f in formulas:
            formula_score += BRIDGE_V3_FORMULA_SCORE.get(f,0)

        coverage=len(slot_set)
        coverage_score=BRIDGE_V3_COVERAGE_SCORE.get(coverage,0)

        try:
            formula_support=int(r.get("Formula Support", len(formulas)))
        except Exception:
            formula_support=len(formulas)

        # V3 core: slot lebih utama, relationship & coverage sebagai bonus.
        total = (
            slot_score*5
            + rel_score*4
            + coverage_score*6
            + formula_score*5
            + formula_support*2
        )

        rows.append({
            "No": r.get("No", fam),
            "Family":fam,
            "Bridge V3 Score":total,
            "Slot Coverage":coverage,
            "Slot List":" / ".join([str(x) for x in slot_list]),
            "Slot Score":slot_score,
            "Relationship Score":rel_score,
            "Coverage Score":coverage_score,
            "Formula Hit Score":formula_score,
            "Formula Support":formula_support,
            "Formula List":r.get("Formula List",""),
            "Reason":f"Slot {slot_score} | Rel {rel_score} | Cov {coverage_score} | F {formula_score} | Sup {formula_support}"
        })
    df=pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), ""
    if "Order" not in df.columns:
        df["Order"] = range(1, len(df)+1)
    df=df.sort_values(["Bridge V3 Score","Slot Coverage","Slot Score","Formula Support","Order"], ascending=[False,False,False,False,True]).reset_index(drop=True)
    df["Rank"]=range(1,len(df)+1)
    top=df.head(top_n)["Family"].astype(str).tolist()
    text="🧩 Rumah A Predictor - Bridge Selection Engine V3\n\n"
    text+=f"🔥 Top {top_n}:\n"
    for i in range(0,len(top),10):
        text+=" / ".join(top[i:i+10])+"\n"
    text+="\n📊 Detail:\n"
    for _,rr in df.head(top_n).iterrows():
        text+=f"{rr['Rank']}. {rr['No']} - Score {rr['Bridge V3 Score']} ({rr['Reason']})\n"
    return df,text


def build_bridge_decision_engine_v31_13(v2_df, v3_df, v2_limit=30, v3_limit=15, top_n=10):
    """
    V31.21 Bridge Decision Engine V1.
    Decision layer sahaja:
    - Ambil Bridge Selection V2 Top30
    - Ambil Bridge Selection V3 Top15
    - Buang duplicate
    - Beri score berdasarkan rank V2 + rank V3
    - Output Top10 dan Top5
    """
    import pandas as pd

    if v2_df is None or v2_df.empty or v3_df is None or v3_df.empty:
        return pd.DataFrame(), ""

    v2 = v2_df.copy().reset_index(drop=True).head(v2_limit)
    v3 = v3_df.copy().reset_index(drop=True).head(v3_limit)

    v2_rank = {pad4(row["Family"]): i+1 for i, row in v2.iterrows()}
    v3_rank = {pad4(row["Family"]): i+1 for i, row in v3.iterrows()}
    display_map = {}
    for _, row in v2.iterrows():
        display_map[pad4(row["Family"])] = pad4(row.get("No", row["Family"]))
    for _, row in v3.iterrows():
        display_map.setdefault(pad4(row["Family"]), pad4(row.get("No", row["Family"])))

    fams = list(dict.fromkeys(list(v2_rank.keys()) + list(v3_rank.keys())))

    rows = []
    for fam in fams:
        r2 = v2_rank.get(fam)
        r3 = v3_rank.get(fam)

        # Rank score: makin kecil rank, makin tinggi score.
        # V2 Top30 = selection/coverage layer.
        # V3 Top15 = decision/aggressive layer.
        score_v2 = (v2_limit + 1 - r2) if r2 is not None else 0
        score_v3 = ((v3_limit + 1 - r3) * 2) if r3 is not None else 0

        agreement_bonus = 20 if (r2 is not None and r3 is not None) else 0
        v3_only_bonus = 5 if (r2 is None and r3 is not None) else 0

        total = score_v2 + score_v3 + agreement_bonus + v3_only_bonus

        source = []
        if r2 is not None:
            source.append(f"V2#{r2}")
        if r3 is not None:
            source.append(f"V3#{r3}")

        rows.append({
            "No": display_map.get(fam, fam),
            "Family": fam,
            "BDE Score": total,
            "V2 Rank": r2 if r2 is not None else "",
            "V3 Rank": r3 if r3 is not None else "",
            "Source": " + ".join(source),
            "Reason": f"V2 {score_v2} | V3 {score_v3} | Agree {agreement_bonus} | V3Only {v3_only_bonus}",
        })

    if rows:
        df = pd.DataFrame(rows)
        if "Order" not in df.columns:
            df["Order"] = range(1, len(df)+1)
    else:
        df = pd.DataFrame(rows)
    df = df.sort_values(
        ["BDE Score", "V3 Rank", "V2 Rank", "Order"],
        ascending=[False, True, True, True]
    ).reset_index(drop=True)
    df["Rank"] = range(1, len(df)+1)

    top = df.head(top_n)["No"].astype(str).tolist()
    top5 = df.head(5)["Family"].astype(str).tolist()

    text = "🏆 Rumah A Predictor - Bridge Decision Engine V1\n\n"
    text += "🔥 Top 5:\n"
    text += " / ".join(top5)
    text += "\n\n🎯 Top 10:\n"
    text += " / ".join(top)
    text += "\n\n📊 Detail:\n"
    for _, r in df.head(top_n).iterrows():
        text += f"{r['Rank']}. {r['No']} - Score {r['BDE Score']} ({r['Source']})\n"

    return df, text


def build_density_decision_engine_v31_8(density_df, ai_nums, pair_pick_df=None, top_n=5):
    """
    V31.8 Density Decision Engine.
    Decision layer sahaja:
    Density + AI 3D overlap + Pair Assist Pick status.
    """
    import pandas as pd

    if density_df is None or density_df.empty or "No" not in density_df.columns:
        return pd.DataFrame(), ""

    ai_nums = [pad4(x) for x in (ai_nums or []) if str(x).strip() != ""]

    pair_rank = {}
    if pair_pick_df is not None and not pair_pick_df.empty and "No" in pair_pick_df.columns:
        pp = pair_pick_df.copy().reset_index(drop=True)
        for i, row in pp.iterrows():
            no = pad4(row.get("No", ""))
            if no:
                pair_rank[no] = "High Priority" if i < 8 else "Watchlist"

    rows = []
    for _, row in density_df.iterrows():
        no = pad4(row.get("No", ""))
        if not no:
            continue

        try:
            support = int(row.get("Support", 0))
        except Exception:
            support = 0

        ai_hits = [an for an in ai_nums if overlap_count_4d(an, no) >= 3]
        if not ai_hits:
            continue

        priority = pair_rank.get(no, "")
        priority_score = 5 if priority == "High Priority" else (2 if priority == "Watchlist" else 0)
        ai_score = len(ai_hits) * 3
        density_score = support
        total_score = density_score + ai_score + priority_score

        rows.append({
            "No": no,
            "Family": no,
            "Score": total_score,
            "Density Support": support,
            "AI Overlap Count": len(ai_hits),
            "AI Match": " / ".join(ai_hits[:10]),
            "Pair Pick": priority if priority else "-",
            "Reason": f"Density ×{support} | AI {len(ai_hits)} | {priority if priority else 'No Pair Pick'}",
        })

    if not rows:
        return pd.DataFrame(), ""

    df = pd.DataFrame(rows).sort_values(
        ["Score", "Density Support", "AI Overlap Count", "Family"],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    top = df.head(top_n)["No"].astype(str).tolist()

    text = "🎯 Rumah A Predictor - Density Decision Engine\n\n"
    text += "🔥 Top 5:\n"
    text += " / ".join(top)
    text += "\n\n📊 Detail:\n"
    for _, r in df.head(15).iterrows():
        text += f"{r['Family']} - Score {r['Score']} ({r['Reason']})\n"

    return df, text


def build_density_pair_source_map_v31_7(overlap_nums, result_pairs):
    """
    Map Pair Assist family -> Density source(s).
    Supaya bila YES, user nampak hit itu datang dari Density mana.
    """
    pair_df, _ = build_pair_assist_all_anchor_safe_v30(overlap_nums, result_pairs)

    source_map = {}
    all_pair_nums = []

    if pair_df is not None and not pair_df.empty:
        for _, row in pair_df.iterrows():
            density_source = str(row.get("Anchor Family", "")).strip().zfill(4)[-4:]
            fams = _split_family_text_to_list(row.get("New Family", ""))

            for fam in fams:
                all_pair_nums.append(fam)
                source_map.setdefault(family4(fam), set()).add(density_source)

    all_pair_nums = list(dict.fromkeys(all_pair_nums))
    return all_pair_nums, source_map


def run_backtest_turbo_v31_7(history_df, test_draws=30):
    """
    V31.7 Backtest Turbo.

    Aliran ringkas:
    AI
    ↓
    Density Overlap
    ↓
    Pair Assist daripada Density
    ↓
    Next Result
    ↓
    YES / NO / PENDING

    Tambahan V31.7:
    - YES tunjuk datang daripada Density mana.
    - Hit Detail lebih jelas.
    - Latest draw tetap muncul sebagai PENDING.
    """
    import pandas as pd
    import time

    t0 = time.perf_counter()

    if history_df is None or history_df.empty or len(history_df) < 30:
        return pd.DataFrame(), pd.DataFrame()

    h = history_df.copy().reset_index(drop=True)
    for c in ["first", "second", "third"]:
        if c in h.columns:
            h[c] = h[c].apply(pad4)

    latest_idx = len(h) - 1
    max_possible_source = latest_idx
    max_tests = max(1, min(int(test_draws), max_possible_source - 20 if max_possible_source > 20 else max_possible_source))
    start_idx = max_possible_source - max_tests + 1
    if start_idx < 5:
        start_idx = 5

    rows = []
    # V31.24.4.1: fixed-origin formula history dibina sekali sebelum test window.
    # Ini lebih pantas dan tetap bebas future leakage kerana draw dalam window
    # tidak digunakan untuk melatih snapshot reliability ini.
    try:
        formula_reliability_bt = build_bridge_formula_reliability_v31_24(
            h.iloc[:start_idx + 1].copy(), lookback=500
        )
    except Exception:
        formula_reliability_bt = {}

    for idx in range(start_idx, max_possible_source + 1):
        try:
            if idx < 5:
                continue

            source = h.iloc[idx]
            has_next_result = idx + 1 < len(h)
            actual = h.iloc[idx + 1] if has_next_result else None
            hist_available = h.iloc[:idx + 1].copy()

            first = pad4(source["first"])
            second = pad4(source["second"])
            third = pad4(source["third"])
            result_pairs = list(dict.fromkeys(get_pairs([first, second, third])))

            # V31.21: Bridge Model audit berasingan.
            try:
                _, bridge_df_bt, _ = build_bridge_model_v31_9(first, second, third)
                bridge_nums = bridge_df_bt["No"] if "No" in bridge_df_bt.columns else bridge_df_bt["Family"].astype(str).tolist() if bridge_df_bt is not None and not bridge_df_bt.empty else []
            except Exception:
                bridge_nums = []
            bridge_fams = set(family4(x) for x in bridge_nums)

            # V31.21: Bridge Selection audit thresholds.
            try:
                bridge_sel_df_bt, _ = build_bridge_selection_engine_v31_10(bridge_df_bt, top_n=60)
                bridge_sel_all = bridge_sel_df_bt["Family"].astype(str).tolist() if bridge_sel_df_bt is not None and not bridge_sel_df_bt.empty else []
                bridge_sel_display_all = bridge_sel_df_bt["No"].astype(str).tolist() if bridge_sel_df_bt is not None and not bridge_sel_df_bt.empty and "No" in bridge_sel_df_bt.columns else bridge_sel_all
            except Exception:
                bridge_sel_df_bt = pd.DataFrame()
                bridge_sel_all = []
                bridge_sel_display_all = []

            bridge_sel_sets = {
                120: set(bridge_sel_all[:120]),
                100: set(bridge_sel_all[:100]),
                80: set(bridge_sel_all[:80]),
                60: set(bridge_sel_all[:60]),
                50: set(bridge_sel_all[:50]),
                40: set(bridge_sel_all[:40]),
                30: set(bridge_sel_all[:30]),
                15: set(bridge_sel_all[:15]),
                5: set(bridge_sel_all[:5]),
            }

            # V31.21: Bridge Selection V2 audit thresholds.
            try:
                bridge_sel_v2_df_bt, _ = build_bridge_selection_engine_v31_11(bridge_df_bt, top_n=60)
                bridge_sel_v2_all = bridge_sel_v2_df_bt["No"] if "No" in v2_df_bt.columns else v2_df_bt["Family"].astype(str).tolist() if bridge_sel_v2_df_bt is not None and not bridge_sel_v2_df_bt.empty else []
            except Exception:
                bridge_sel_v2_df_bt = pd.DataFrame()
                bridge_sel_v2_all = []
                bridge_sel_v2_display_all = []

            bridge_sel_v2_sets = {
                120: set(bridge_sel_v2_all[:120]),
                100: set(bridge_sel_v2_all[:100]),
                80: set(bridge_sel_v2_all[:80]),
                60: set(bridge_sel_v2_all[:60]),
                50: set(bridge_sel_v2_all[:50]),
                40: set(bridge_sel_v2_all[:40]),
                30: set(bridge_sel_v2_all[:30]),
                15: set(bridge_sel_v2_all[:15]),
                5: set(bridge_sel_v2_all[:5]),
            }

            # V31.21: Bridge Selection V3 audit thresholds.
            try:
                bridge_sel_v3_df_bt, _ = build_bridge_selection_engine_v31_12(bridge_df_bt, top_n=60)
                bridge_sel_v3_all = bridge_sel_v3_df_bt["No"] if "No" in v3_df_bt.columns else v3_df_bt["Family"].astype(str).tolist() if bridge_sel_v3_df_bt is not None and not bridge_sel_v3_df_bt.empty else []
            except Exception:
                bridge_sel_v3_df_bt = pd.DataFrame()
                bridge_sel_v3_all = []
                bridge_sel_v3_display_all = []

            bridge_sel_v3_sets = {
                120: set(bridge_sel_v3_all[:120]),
                100: set(bridge_sel_v3_all[:100]),
                80: set(bridge_sel_v3_all[:80]),
                60: set(bridge_sel_v3_all[:60]),
                50: set(bridge_sel_v3_all[:50]),
                40: set(bridge_sel_v3_all[:40]),
                30: set(bridge_sel_v3_all[:30]),
                15: set(bridge_sel_v3_all[:15]),
                5: set(bridge_sel_v3_all[:5]),
            }

            # V31.21: Bridge Decision Engine V1 backtest.
            try:
                bde_df_bt, _ = build_bridge_decision_engine_v31_13(
                    bridge_sel_v2_df_bt,
                    bridge_sel_v3_df_bt,
                    v2_limit=30,
                    v3_limit=15,
                    top_n=10,
                )
                bde_all = bde_df_bt["No"] if "No" in bde_df_bt.columns else bde_df_bt["Family"].astype(str).tolist() if bde_df_bt is not None and not bde_df_bt.empty else []
            except Exception:
                bde_df_bt = pd.DataFrame()
                bde_all = []
                bde_display_all = []

            bde_sets = {
                10: set(bde_all[:10]),
                5: set(bde_all[:5]),
            }

            # Generate core result once. UI/display tidak dipanggil dalam backtest.
            result_bt = generate(hist_available, first, second, third)

            # V31.7.1 TURBO LITE:
            # Jangan panggil model_accuracy_tracker() dan champion_engine_v19() dalam backtest.
            # Dua fungsi ini sangat berat bila loop banyak draw.
            # Guna hybrid_all daripada generate() sebagai AI candidates ringan.
            ai_nums = get_ranked_no_list_for_backtest(result_bt.get("hybrid_all", pd.DataFrame()), limit=15)

            # Fallback: jika hybrid_all tiada, ambil gabungan 4 model utama.
            if not ai_nums:
                ai_nums = []
                for key, lim in [("stat", 10), ("position", 10), ("pair", 10), ("theory", 20)]:
                    for n in get_ranked_no_list_for_backtest(result_bt.get(key, pd.DataFrame()), limit=lim):
                        if n not in ai_nums:
                            ai_nums.append(n)
                ai_nums = ai_nums[:15]

            # Anchor dari 4 model utama sahaja.
            model_stat = get_ranked_no_list_for_backtest(result_bt.get("stat", pd.DataFrame()), limit=10)
            model_position = get_ranked_no_list_for_backtest(result_bt.get("position", pd.DataFrame()), limit=10)
            model_pair = get_ranked_no_list_for_backtest(result_bt.get("pair", pd.DataFrame()), limit=10)
            model_nodouble = get_ranked_no_list_for_backtest(result_bt.get("theory", pd.DataFrame()), limit=20)

            acc_sources = [
                ("Statistik", model_stat),
                ("Peralihan", model_position),
                ("Pasangan", model_pair),
                ("No Double", model_nodouble),
            ]
            acc_df_bt = build_anchor_cluster_convergence_v30(acc_sources, top_families=10)
            anchor_families = acc_df_bt["Family"].astype(str).tolist() if acc_df_bt is not None and not acc_df_bt.empty and "Family" in acc_df_bt.columns else []
            # V31.24.2: seluruh confirmation flow menggunakan Anchor, bukan AI/Hybrid lama.
            ai_nums = anchor_families

            pair_df_bt, _ = build_pair_assist_all_anchor_safe_v30(anchor_families, result_pairs)
            density_df_bt, _ = build_anchor_density_signal_v31(pair_df_bt, min_support=2, top_n=30)
            density_nums = density_df_bt["No"].astype(str).tolist() if density_df_bt is not None and not density_df_bt.empty else []

            # V31.8.2: bina DDE ranking untuk audit backtest.
            try:
                pair_pick_df_bt = build_pair_assist_pick_engine_v30(
                    pair_df_bt,
                    result_pairs,
                    anchor_families=anchor_families,
                    top_n=20,
                )
            except Exception:
                pair_pick_df_bt = pd.DataFrame()

            try:
                dde_df_bt, _ = build_density_decision_engine_v31_8(
                    density_df_bt,
                    ai_nums,
                    pair_pick_df=pair_pick_df_bt,
                    top_n=5,
                )
            except Exception:
                dde_df_bt = pd.DataFrame()

            dde_rank_map = {}
            dde_score_map = {}
            if dde_df_bt is not None and not dde_df_bt.empty and "Family" in dde_df_bt.columns:
                for _i, _r in dde_df_bt.reset_index(drop=True).iterrows():
                    _fam = pad4(_r.get("Family", ""))
                    dde_rank_map[_fam] = int(_i) + 1
                    try:
                        dde_score_map[_fam] = _r.get("Score", "")
                    except Exception:
                        dde_score_map[_fam] = ""

            dde_all_list = dde_df_bt["Family"].astype(str).tolist() if dde_df_bt is not None and not dde_df_bt.empty and "Family" in dde_df_bt.columns else []
            dde_top5_list = dde_all_list[:5]

            # V31.24: Family Ranker tanpa Full Result semasa backtest untuk elak future leakage.
            try:
                family_rank_bt, _ = build_bridge_family_ranker_v31_24(
                    bridge_df_bt,
                    model_sources=acc_sources,
                    ai_nums=[],
                    anchor_df=acc_df_bt,
                    density_df=dde_df_bt,
                    full_support={},
                    formula_reliability=formula_reliability_bt,
                    top_n=10,
                )
            except Exception:
                family_rank_bt = pd.DataFrame()
            if family_rank_bt is not None and not family_rank_bt.empty:
                family_conviction_list = family_rank_bt.sort_values("Conviction Rank")["Family"].astype(str).tolist()
                family_balanced_list = family_rank_bt.sort_values("Balanced Rank")["Family"].astype(str).tolist()
            else:
                family_conviction_list = []
                family_balanced_list = []
            family_conviction_map = {f: i + 1 for i, f in enumerate(family_conviction_list)}
            family_balanced_map = {f: i + 1 for i, f in enumerate(family_balanced_list)}

            # Density yang overlap 3D dengan AI.
            overlap_nums = []
            overlap_pairs = []
            density_ai_source = {}
            for dn in density_nums:
                hits = []
                for an in ai_nums:
                    if overlap_count_4d(an, dn) >= 3:
                        hits.append(an)
                if hits:
                    overlap_nums.append(dn)
                    density_ai_source[dn] = hits[:5]
                    overlap_pairs.append(f"{' + '.join(hits[:3])} ↔ {dn}")

            overlap_nums = list(dict.fromkeys(overlap_nums))

            # Pair Assist daripada Density overlap sahaja + source map.
            density_pair_nums, source_map = build_density_pair_source_map_v31_7(overlap_nums, result_pairs)
            density_pair_fams = set(family4(n) for n in density_pair_nums)

            if has_next_result:
                actual_nums = [pad4(actual["first"]), pad4(actual["second"]), pad4(actual["third"])]
                actual_fams = [family4(n) for n in actual_nums]

                bridge_hit_nums = [actual_nums[i] for i, f in enumerate(actual_fams) if f in bridge_fams]
                bridge_hit = "YES" if bridge_hit_nums else "NO"
                bridge_hit_number = " / ".join(bridge_hit_nums)

                family_rank_hit_nums = [actual_nums[i] for i, f in enumerate(actual_fams) if f in family_conviction_map]
                family_conviction_hit_ranks = [family_conviction_map[f] for f in actual_fams if f in family_conviction_map]
                family_balanced_hit_ranks = [family_balanced_map[f] for f in actual_fams if f in family_balanced_map]
                family_conviction_best = min(family_conviction_hit_ranks) if family_conviction_hit_ranks else ""
                family_balanced_best = min(family_balanced_hit_ranks) if family_balanced_hit_ranks else ""
                family_conviction_top3_hit = "YES" if family_conviction_hit_ranks and min(family_conviction_hit_ranks) <= 3 else "NO"
                family_conviction_top5_hit = "YES" if family_conviction_hit_ranks and min(family_conviction_hit_ranks) <= 5 else "NO"
                family_balanced_top10_hit = "YES" if family_balanced_hit_ranks and min(family_balanced_hit_ranks) <= 10 else "NO"

                def _bridge_sel_hit(n):
                    vals = [actual_nums[i] for i, f in enumerate(actual_fams) if f in bridge_sel_sets.get(n, set())]
                    return ("YES" if vals else "NO", " / ".join(vals))

                bridge_sel_120_hit, bridge_sel_120_hit_no = _bridge_sel_hit(120)
                bridge_sel_100_hit, bridge_sel_100_hit_no = _bridge_sel_hit(100)
                bridge_sel_80_hit, bridge_sel_80_hit_no = _bridge_sel_hit(80)
                bridge_sel_60_hit, bridge_sel_60_hit_no = _bridge_sel_hit(60)
                bridge_sel_50_hit, bridge_sel_50_hit_no = _bridge_sel_hit(50)
                bridge_sel_40_hit, bridge_sel_40_hit_no = _bridge_sel_hit(40)
                bridge_sel_30_hit, bridge_sel_30_hit_no = _bridge_sel_hit(30)
                bridge_sel_15_hit, bridge_sel_15_hit_no = _bridge_sel_hit(15)
                bridge_sel_5_hit, bridge_sel_5_hit_no = _bridge_sel_hit(5)

                def _bridge_sel_v2_hit(n):
                    vals = [actual_nums[i] for i, f in enumerate(actual_fams) if f in bridge_sel_v2_sets.get(n, set())]
                    return ("YES" if vals else "NO", " / ".join(vals))

                bridge_v2_120_hit, bridge_v2_120_hit_no = _bridge_sel_v2_hit(120)
                bridge_v2_100_hit, bridge_v2_100_hit_no = _bridge_sel_v2_hit(100)
                bridge_v2_80_hit, bridge_v2_80_hit_no = _bridge_sel_v2_hit(80)
                bridge_v2_60_hit, bridge_v2_60_hit_no = _bridge_sel_v2_hit(60)
                bridge_v2_50_hit, bridge_v2_50_hit_no = _bridge_sel_v2_hit(50)
                bridge_v2_40_hit, bridge_v2_40_hit_no = _bridge_sel_v2_hit(40)
                bridge_v2_30_hit, bridge_v2_30_hit_no = _bridge_sel_v2_hit(30)
                bridge_v2_15_hit, bridge_v2_15_hit_no = _bridge_sel_v2_hit(15)
                bridge_v2_5_hit, bridge_v2_5_hit_no = _bridge_sel_v2_hit(5)

                def _bridge_sel_v3_hit(n):
                    vals = [actual_nums[i] for i, f in enumerate(actual_fams) if f in bridge_sel_v3_sets.get(n, set())]
                    return ("YES" if vals else "NO", " / ".join(vals))

                bridge_v3_120_hit, bridge_v3_120_hit_no = _bridge_sel_v3_hit(120)
                bridge_v3_100_hit, bridge_v3_100_hit_no = _bridge_sel_v3_hit(100)
                bridge_v3_80_hit, bridge_v3_80_hit_no = _bridge_sel_v3_hit(80)
                bridge_v3_60_hit, bridge_v3_60_hit_no = _bridge_sel_v3_hit(60)
                bridge_v3_50_hit, bridge_v3_50_hit_no = _bridge_sel_v3_hit(50)
                bridge_v3_40_hit, bridge_v3_40_hit_no = _bridge_sel_v3_hit(40)
                bridge_v3_30_hit, bridge_v3_30_hit_no = _bridge_sel_v3_hit(30)
                bridge_v3_15_hit, bridge_v3_15_hit_no = _bridge_sel_v3_hit(15)
                bridge_v3_5_hit, bridge_v3_5_hit_no = _bridge_sel_v3_hit(5)

                def _bde_hit(n):
                    vals = [actual_nums[i] for i, f in enumerate(actual_fams) if f in bde_sets.get(n, set())]
                    return ("YES" if vals else "NO", " / ".join(vals))

                bde_top10_hit, bde_top10_hit_no = _bde_hit(10)
                bde_top5_hit, bde_top5_hit_no = _bde_hit(5)

                bde_hit_ranks = []
                bde_hit_scores = []
                bde_hit_details = []
                try:
                    if bde_df_bt is not None and not bde_df_bt.empty:
                        _bde_rank_map = {pad4(r["Family"]): int(r["Rank"]) for _, r in bde_df_bt.iterrows() if "Family" in r and "Rank" in r}
                        _bde_score_map = {pad4(r["Family"]): r.get("BDE Score", "") for _, r in bde_df_bt.iterrows() if "Family" in r}
                        for actual_no, actual_fam in zip(actual_nums, actual_fams):
                            if actual_fam in _bde_rank_map:
                                bde_hit_ranks.append(str(_bde_rank_map.get(actual_fam, "")))
                                bde_hit_scores.append(str(_bde_score_map.get(actual_fam, "")))
                                bde_hit_details.append(f"{actual_no} | Rank {_bde_rank_map.get(actual_fam, '')} | Score {_bde_score_map.get(actual_fam, '')}")
                except Exception:
                    pass

                bde_best_rank = ""
                if bde_hit_ranks:
                    try:
                        bde_best_rank = str(min([int(x) for x in bde_hit_ranks if str(x).isdigit()]))
                    except Exception:
                        bde_best_rank = ""

                bde_hit_rank = " / ".join(list(dict.fromkeys(bde_hit_ranks)))
                bde_hit_score = " / ".join(list(dict.fromkeys(bde_hit_scores)))
                bde_hit_detail = " / ".join(list(dict.fromkeys(bde_hit_details)))

                hit_nums = []
                hit_density_sources = []
                hit_ai_sources = []
                hit_pair_families = []
                hit_detail_rows = []

                for actual_no, actual_fam in zip(actual_nums, actual_fams):
                    if actual_fam in density_pair_fams:
                        hit_nums.append(actual_no)

                        # Pair Assist family yang sama dengan result sebenar.
                        # Contoh result 9926 -> family 2699.
                        hit_pair_family = actual_fam
                        hit_pair_families.append(hit_pair_family)

                        src_density = sorted(list(source_map.get(actual_fam, [])))
                        hit_density_sources.extend(src_density)

                        for ds in src_density:
                            ai_list = density_ai_source.get(ds, [])
                            hit_ai_sources.extend(ai_list)

                            ai_text = " + ".join(ai_list) if ai_list else "-"
                            hit_detail_rows.append(
                                f"AI {ai_text} | Density {ds} | Pair Assist Family {hit_pair_family} | Result {actual_no}"
                            )

                hit_density_sources = list(dict.fromkeys(hit_density_sources))
                hit_ai_sources = list(dict.fromkeys(hit_ai_sources))
                hit_pair_families = list(dict.fromkeys(hit_pair_families))
                hit_detail_rows = list(dict.fromkeys(hit_detail_rows))

                # DDE rank/score untuk density source yang menghasilkan hit.
                hit_dde_ranks = []
                hit_dde_scores = []
                for ds in hit_density_sources:
                    if ds in dde_rank_map:
                        hit_dde_ranks.append(str(dde_rank_map.get(ds, "")))
                        hit_dde_scores.append(str(dde_score_map.get(ds, "")))

                hit_dde_rank = " / ".join(list(dict.fromkeys(hit_dde_ranks)))
                hit_dde_score = " / ".join(list(dict.fromkeys(hit_dde_scores)))

                if hit_dde_ranks:
                    try:
                        best_rank = min([int(x) for x in hit_dde_ranks if str(x).isdigit()])
                    except Exception:
                        best_rank = None

                    if best_rank == 1:
                        hit_dde_group = "Top 1"
                    elif best_rank is not None and best_rank <= 3:
                        hit_dde_group = "Top 3"
                    elif best_rank is not None and best_rank <= 5:
                        hit_dde_group = "Top 5"
                    elif best_rank is not None and best_rank <= 10:
                        hit_dde_group = "Top 10"
                    elif best_rank is not None:
                        hit_dde_group = "Top 15+"
                    else:
                        hit_dde_group = ""
                else:
                    hit_dde_group = ""

                hit_status = "YES" if hit_nums else "NO"
                next_draw = str(actual.get("draw_no", idx + 1))
                next_result = " / ".join(actual_nums)
                hit_number = " / ".join(hit_nums)
                hit_from_density = " / ".join(hit_density_sources)
                hit_ai_match = " / ".join(hit_ai_sources)
                hit_pair_family = " / ".join(hit_pair_families)
                hit_detail = " / ".join(hit_detail_rows)
            else:
                hit_status = "PENDING"
                next_draw = ""
                next_result = "Belum ada next draw"
                hit_number = ""
                bridge_hit = "PENDING"
                bridge_hit_number = ""
                family_rank_hit_nums = []
                family_conviction_best = ""
                family_balanced_best = ""
                family_conviction_top3_hit = family_conviction_top5_hit = family_balanced_top10_hit = "PENDING"
                bridge_sel_120_hit = bridge_sel_100_hit = bridge_sel_80_hit = bridge_sel_60_hit = "PENDING"
                bridge_sel_50_hit = bridge_sel_40_hit = bridge_sel_30_hit = bridge_sel_15_hit = bridge_sel_5_hit = "PENDING"
                bridge_sel_120_hit_no = bridge_sel_100_hit_no = bridge_sel_80_hit_no = bridge_sel_60_hit_no = ""
                bridge_sel_50_hit_no = bridge_sel_40_hit_no = bridge_sel_30_hit_no = bridge_sel_15_hit_no = bridge_sel_5_hit_no = ""
                bridge_v2_120_hit = bridge_v2_100_hit = bridge_v2_80_hit = bridge_v2_60_hit = "PENDING"
                bridge_v2_50_hit = bridge_v2_40_hit = bridge_v2_30_hit = bridge_v2_15_hit = bridge_v2_5_hit = "PENDING"
                bridge_v2_120_hit_no = bridge_v2_100_hit_no = bridge_v2_80_hit_no = bridge_v2_60_hit_no = ""
                bridge_v2_50_hit_no = bridge_v2_40_hit_no = bridge_v2_30_hit_no = bridge_v2_15_hit_no = bridge_v2_5_hit_no = ""
                bridge_v3_120_hit = bridge_v3_100_hit = bridge_v3_80_hit = bridge_v3_60_hit = "PENDING"
                bridge_v3_50_hit = bridge_v3_40_hit = bridge_v3_30_hit = bridge_v3_15_hit = bridge_v3_5_hit = "PENDING"
                bridge_v3_120_hit_no = bridge_v3_100_hit_no = bridge_v3_80_hit_no = bridge_v3_60_hit_no = ""
                bridge_v3_50_hit_no = bridge_v3_40_hit_no = bridge_v3_30_hit_no = bridge_v3_15_hit_no = bridge_v3_5_hit_no = ""
                bde_top10_hit = bde_top5_hit = "PENDING"
                bde_top10_hit_no = bde_top5_hit_no = ""
                bde_best_rank = ""
                bde_hit_rank = ""
                bde_hit_score = ""
                bde_hit_detail = ""
                hit_from_density = ""
                hit_ai_match = ""
                hit_pair_family = ""
                hit_detail = ""
                hit_dde_rank = ""
                hit_dde_score = ""
                hit_dde_group = ""

            rows.append({
                "Source Draw": str(source.get("draw_no", idx)),
                "Source Result": f"{first} / {second} / {third}",
                "Next Draw": next_draw,
                "Next Result": next_result,
                "AI Candidates": " / ".join(ai_nums),
                "Density Overlap Count": len(overlap_nums),
                "Density Overlap List": " / ".join(overlap_nums),
                "AI ↔ Density Match": " / ".join(overlap_pairs[:30]),
                "Bridge Count": len(bridge_nums),
                "Bridge List": " / ".join(bridge_nums),
                "Bridge Hit": bridge_hit,
                "Bridge Hit Number": bridge_hit_number,
                "Family Ranker Conviction Top 5": " / ".join(family_conviction_list[:5]),
                "Family Ranker Balanced Top 10": " / ".join(family_balanced_list[:10]),
                "Family Ranker Conviction Top3 Hit": family_conviction_top3_hit,
                "Family Ranker Conviction Top5 Hit": family_conviction_top5_hit,
                "Family Ranker Balanced Top10 Hit": family_balanced_top10_hit,
                "Family Ranker Hit Number": " / ".join(family_rank_hit_nums),
                "Family Ranker Conviction Best Rank": family_conviction_best,
                "Family Ranker Balanced Best Rank": family_balanced_best,
                "Bridge Selection Count": len(bridge_sel_all),
                "Bridge Selection Top 60": " / ".join(bridge_sel_display_all[:60]),
                "Bridge Sel Top120 Hit": bridge_sel_120_hit,
                "Bridge Sel Top120 Hit Number": bridge_sel_120_hit_no,
                "Bridge Sel Top100 Hit": bridge_sel_100_hit,
                "Bridge Sel Top100 Hit Number": bridge_sel_100_hit_no,
                "Bridge Sel Top80 Hit": bridge_sel_80_hit,
                "Bridge Sel Top80 Hit Number": bridge_sel_80_hit_no,
                "Bridge Sel Top60 Hit": bridge_sel_60_hit,
                "Bridge Sel Top60 Hit Number": bridge_sel_60_hit_no,
                "Bridge Sel Top50 Hit": bridge_sel_50_hit,
                "Bridge Sel Top50 Hit Number": bridge_sel_50_hit_no,
                "Bridge Sel Top40 Hit": bridge_sel_40_hit,
                "Bridge Sel Top40 Hit Number": bridge_sel_40_hit_no,
                "Bridge Sel Top30 Hit": bridge_sel_30_hit,
                "Bridge Sel Top30 Hit Number": bridge_sel_30_hit_no,
                "Bridge Sel Top15 Hit": bridge_sel_15_hit,
                "Bridge Sel Top15 Hit Number": bridge_sel_15_hit_no,
                "Bridge Sel Top5 Hit": bridge_sel_5_hit,
                "Bridge Sel Top5 Hit Number": bridge_sel_5_hit_no,
                "Bridge V2 Selection Count": len(bridge_sel_v2_all),
                "Bridge V2 Selection Top 60": " / ".join(bridge_sel_v2_display_all[:60]),
                "Bridge V2 Top120 Hit": bridge_v2_120_hit,
                "Bridge V2 Top120 Hit Number": bridge_v2_120_hit_no,
                "Bridge V2 Top100 Hit": bridge_v2_100_hit,
                "Bridge V2 Top100 Hit Number": bridge_v2_100_hit_no,
                "Bridge V2 Top80 Hit": bridge_v2_80_hit,
                "Bridge V2 Top80 Hit Number": bridge_v2_80_hit_no,
                "Bridge V2 Top60 Hit": bridge_v2_60_hit,
                "Bridge V2 Top60 Hit Number": bridge_v2_60_hit_no,
                "Bridge V2 Top50 Hit": bridge_v2_50_hit,
                "Bridge V2 Top50 Hit Number": bridge_v2_50_hit_no,
                "Bridge V2 Top40 Hit": bridge_v2_40_hit,
                "Bridge V2 Top40 Hit Number": bridge_v2_40_hit_no,
                "Bridge V2 Top30 Hit": bridge_v2_30_hit,
                "Bridge V2 Top30 Hit Number": bridge_v2_30_hit_no,
                "Bridge V2 Top15 Hit": bridge_v2_15_hit,
                "Bridge V2 Top15 Hit Number": bridge_v2_15_hit_no,
                "Bridge V2 Top5 Hit": bridge_v2_5_hit,
                "Bridge V2 Top5 Hit Number": bridge_v2_5_hit_no,
                "Bridge V3 Selection Count": len(bridge_sel_v3_all),
                "Bridge V3 Selection Top 60": " / ".join(bridge_sel_v3_display_all[:60]),
                "Bridge V3 Top120 Hit": bridge_v3_120_hit,
                "Bridge V3 Top120 Hit Number": bridge_v3_120_hit_no,
                "Bridge V3 Top100 Hit": bridge_v3_100_hit,
                "Bridge V3 Top100 Hit Number": bridge_v3_100_hit_no,
                "Bridge V3 Top80 Hit": bridge_v3_80_hit,
                "Bridge V3 Top80 Hit Number": bridge_v3_80_hit_no,
                "Bridge V3 Top60 Hit": bridge_v3_60_hit,
                "Bridge V3 Top60 Hit Number": bridge_v3_60_hit_no,
                "Bridge V3 Top50 Hit": bridge_v3_50_hit,
                "Bridge V3 Top50 Hit Number": bridge_v3_50_hit_no,
                "Bridge V3 Top40 Hit": bridge_v3_40_hit,
                "Bridge V3 Top40 Hit Number": bridge_v3_40_hit_no,
                "Bridge V3 Top30 Hit": bridge_v3_30_hit,
                "Bridge V3 Top30 Hit Number": bridge_v3_30_hit_no,
                "Bridge V3 Top15 Hit": bridge_v3_15_hit,
                "Bridge V3 Top15 Hit Number": bridge_v3_15_hit_no,
                "Bridge V3 Top5 Hit": bridge_v3_5_hit,
                "Bridge V3 Top5 Hit Number": bridge_v3_5_hit_no,
                "BDE Count": len(bde_all),
                "BDE Top 10": " / ".join((bde_display_all if 'bde_display_all' in locals() else bde_all)[:10]),
                "BDE Top 5": " / ".join((bde_display_all if 'bde_display_all' in locals() else bde_all)[:5]),
                "BDE Top10 Hit": bde_top10_hit,
                "BDE Top10 Hit Number": bde_top10_hit_no,
                "BDE Top5 Hit": bde_top5_hit,
                "BDE Top5 Hit Number": bde_top5_hit_no,
                "BDE Best Rank": bde_best_rank,
                "BDE Hit Rank": bde_hit_rank,
                "BDE Hit Score": bde_hit_score,
                "BDE Hit Detail": bde_hit_detail,
                "BDE Hit Group": "Top5" if bde_top5_hit == "YES" else ("Top10" if bde_top10_hit == "YES" else ("PENDING" if bde_top10_hit == "PENDING" else "NO")),
                "Pair Assist From Density Count": len(density_pair_nums),
                "DDE Count": len(dde_all_list),
                "DDE Top 5": " / ".join(dde_top5_list),
                "DDE All List": " / ".join(dde_all_list),
                "Hit": hit_status,
                "Hit Number": hit_number,
                "Hit AI Match": hit_ai_match,
                "Hit Density Source": hit_from_density,
                "Hit Pair Assist Family": hit_pair_family,
                "Hit Detail": hit_detail,
                "Hit DDE Rank": hit_dde_rank,
                "Hit DDE Score": hit_dde_score,
                "Hit DDE Group": hit_dde_group,
            })

        except Exception as e:
            rows.append({
                "Source Draw": str(h.iloc[idx].get("draw_no", idx)) if idx < len(h) else "",
                "Hit": "ERROR",
                "Error": str(e),
            })

    detail_df = pd.DataFrame(rows)
    for col in [c for c in detail_df.columns if "Rank" in str(c)]:
        detail_df[col] = detail_df[col].fillna("").astype(str)

    if detail_df.empty:
        return pd.DataFrame(), detail_df

    valid = detail_df[detail_df.get("Hit", "").astype(str).isin(["YES", "NO"])].copy()
    pending = detail_df[detail_df.get("Hit", "").astype(str).eq("PENDING")].copy()
    total = len(valid)
    yes = int(valid["Hit"].eq("YES").sum()) if total else 0
    no = int(valid["Hit"].eq("NO").sum()) if total else 0

    elapsed = round(time.perf_counter() - t0, 2)

    summary_df = pd.DataFrame([
        {"Metric": "Tested source draws", "Value": total},
        {"Metric": "Pending latest draw", "Value": len(pending)},
        {"Metric": "YES", "Value": yes},
        {"Metric": "NO", "Value": no},
        {"Metric": "Hit Rate %", "Value": round((yes / total) * 100, 1) if total else 0},
        {"Metric": "Bridge YES", "Value": int(valid["Bridge Hit"].eq("YES").sum()) if total and "Bridge Hit" in valid.columns else 0},
        {"Metric": "Bridge Hit Rate %", "Value": round((valid["Bridge Hit"].eq("YES").sum() / total) * 100, 1) if total and "Bridge Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top120 YES", "Value": int(valid["Bridge Sel Top120 Hit"].eq("YES").sum()) if total and "Bridge Sel Top120 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top100 YES", "Value": int(valid["Bridge Sel Top100 Hit"].eq("YES").sum()) if total and "Bridge Sel Top100 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top80 YES", "Value": int(valid["Bridge Sel Top80 Hit"].eq("YES").sum()) if total and "Bridge Sel Top80 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top60 YES", "Value": int(valid["Bridge Sel Top60 Hit"].eq("YES").sum()) if total and "Bridge Sel Top60 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top50 YES", "Value": int(valid["Bridge Sel Top50 Hit"].eq("YES").sum()) if total and "Bridge Sel Top50 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top40 YES", "Value": int(valid["Bridge Sel Top40 Hit"].eq("YES").sum()) if total and "Bridge Sel Top40 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top30 YES", "Value": int(valid["Bridge Sel Top30 Hit"].eq("YES").sum()) if total and "Bridge Sel Top30 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top15 YES", "Value": int(valid["Bridge Sel Top15 Hit"].eq("YES").sum()) if total and "Bridge Sel Top15 Hit" in valid.columns else 0},
        {"Metric": "Bridge Selection Top5 YES", "Value": int(valid["Bridge Sel Top5 Hit"].eq("YES").sum()) if total and "Bridge Sel Top5 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top120 YES", "Value": int(valid["Bridge V2 Top120 Hit"].eq("YES").sum()) if total and "Bridge V2 Top120 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top100 YES", "Value": int(valid["Bridge V2 Top100 Hit"].eq("YES").sum()) if total and "Bridge V2 Top100 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top80 YES", "Value": int(valid["Bridge V2 Top80 Hit"].eq("YES").sum()) if total and "Bridge V2 Top80 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top60 YES", "Value": int(valid["Bridge V2 Top60 Hit"].eq("YES").sum()) if total and "Bridge V2 Top60 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top50 YES", "Value": int(valid["Bridge V2 Top50 Hit"].eq("YES").sum()) if total and "Bridge V2 Top50 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top40 YES", "Value": int(valid["Bridge V2 Top40 Hit"].eq("YES").sum()) if total and "Bridge V2 Top40 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top30 YES", "Value": int(valid["Bridge V2 Top30 Hit"].eq("YES").sum()) if total and "Bridge V2 Top30 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top15 YES", "Value": int(valid["Bridge V2 Top15 Hit"].eq("YES").sum()) if total and "Bridge V2 Top15 Hit" in valid.columns else 0},
        {"Metric": "Bridge V2 Top5 YES", "Value": int(valid["Bridge V2 Top5 Hit"].eq("YES").sum()) if total and "Bridge V2 Top5 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top120 YES", "Value": int(valid["Bridge V3 Top120 Hit"].eq("YES").sum()) if total and "Bridge V3 Top120 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top100 YES", "Value": int(valid["Bridge V3 Top100 Hit"].eq("YES").sum()) if total and "Bridge V3 Top100 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top80 YES", "Value": int(valid["Bridge V3 Top80 Hit"].eq("YES").sum()) if total and "Bridge V3 Top80 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top60 YES", "Value": int(valid["Bridge V3 Top60 Hit"].eq("YES").sum()) if total and "Bridge V3 Top60 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top50 YES", "Value": int(valid["Bridge V3 Top50 Hit"].eq("YES").sum()) if total and "Bridge V3 Top50 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top40 YES", "Value": int(valid["Bridge V3 Top40 Hit"].eq("YES").sum()) if total and "Bridge V3 Top40 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top30 YES", "Value": int(valid["Bridge V3 Top30 Hit"].eq("YES").sum()) if total and "Bridge V3 Top30 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top15 YES", "Value": int(valid["Bridge V3 Top15 Hit"].eq("YES").sum()) if total and "Bridge V3 Top15 Hit" in valid.columns else 0},
        {"Metric": "Bridge V3 Top5 YES", "Value": int(valid["Bridge V3 Top5 Hit"].eq("YES").sum()) if total and "Bridge V3 Top5 Hit" in valid.columns else 0},
        {"Metric": "BDE Top10 YES", "Value": int(valid["BDE Top10 Hit"].eq("YES").sum()) if total and "BDE Top10 Hit" in valid.columns else 0},
        {"Metric": "BDE Top5 YES", "Value": int(valid["BDE Top5 Hit"].eq("YES").sum()) if total and "BDE Top5 Hit" in valid.columns else 0},
        {"Metric": "BDE Top5 Hit Rate %", "Value": round((valid["BDE Top5 Hit"].eq("YES").sum() / total) * 100, 1) if total and "BDE Top5 Hit" in valid.columns else 0},
        {"Metric": "BDE Top10 Hit Rate %", "Value": round((valid["BDE Top10 Hit"].eq("YES").sum() / total) * 100, 1) if total and "BDE Top10 Hit" in valid.columns else 0},
        {"Metric": "BDE Top5 Group Count", "Value": int(valid["BDE Hit Group"].eq("Top5").sum()) if total and "BDE Hit Group" in valid.columns else 0},
        {"Metric": "BDE Top10 Only Group Count", "Value": int(valid["BDE Hit Group"].eq("Top10").sum()) if total and "BDE Hit Group" in valid.columns else 0},
        {"Metric": "YES in DDE Top 1", "Value": int(valid["Hit DDE Group"].eq("Top 1").sum()) if total and "Hit DDE Group" in valid.columns else 0},
        {"Metric": "YES in DDE Top 3", "Value": int(valid["Hit DDE Group"].isin(["Top 1", "Top 3"]).sum()) if total and "Hit DDE Group" in valid.columns else 0},
        {"Metric": "YES in DDE Top 5", "Value": int(valid["Hit DDE Group"].isin(["Top 1", "Top 3", "Top 5"]).sum()) if total and "Hit DDE Group" in valid.columns else 0},
        {"Metric": "YES in DDE Top 10", "Value": int(valid["Hit DDE Group"].isin(["Top 1", "Top 3", "Top 5", "Top 10"]).sum()) if total and "Hit DDE Group" in valid.columns else 0},
        {"Metric": "Average Density Overlap Count", "Value": round(valid["Density Overlap Count"].mean(), 1) if total and "Density Overlap Count" in valid.columns else 0},
        {"Metric": "Average Pair Assist From Density Count", "Value": round(valid["Pair Assist From Density Count"].mean(), 1) if total and "Pair Assist From Density Count" in valid.columns else 0},
        {"Metric": "Elapsed Seconds", "Value": elapsed},
    ])

    return summary_df, detail_df

def run_simple_backtest_v31_6(history_df, test_draws=30):
    """
    V31.6 Simple Backtest.

    Aliran:
    AI candidates
    ↓
    Density Overlap 3D
    ↓
    Pair Assist daripada Density
    ↓
    Result next draw
    ↓
    YES / NO

    Penting:
    - Draw terakhir tidak diuji sebab belum ada next draw.
    - Tiada metrik lain yang mengelirukan.
    """
    import pandas as pd

    if history_df is None or history_df.empty or len(history_df) < 30:
        return pd.DataFrame(), pd.DataFrame()

    h = history_df.copy().reset_index(drop=True)
    for c in ["first", "second", "third"]:
        if c in h.columns:
            h[c] = h[c].apply(pad4)

    # V31.6.1:
    # Masukkan juga latest source draw dalam detail.
    # Kalau belum ada next draw, status = PENDING, bukan dibuang.
    latest_idx = len(h) - 1
    max_possible_source = latest_idx
    max_tests = max(1, min(int(test_draws), max_possible_source - 20 if max_possible_source > 20 else max_possible_source))
    start_idx = max_possible_source - max_tests + 1
    if start_idx < 5:
        start_idx = 5

    rows = []

    for idx in range(start_idx, max_possible_source + 1):
        try:
            if idx < 5:
                continue

            source = h.iloc[idx]
            has_next_result = idx + 1 < len(h)
            actual = h.iloc[idx + 1] if has_next_result else None

            hist_available = h.iloc[:idx + 1].copy()

            first = pad4(source["first"])
            second = pad4(source["second"])
            third = pad4(source["third"])

            result_bt = generate(hist_available, first, second, third)

            # AI candidates = AI Pick + Top3 + Strong Buy + Backup = top 15 champion.
            try:
                accuracy_df_bt = model_accuracy_tracker(hist_available, lookback=100)
                decision_df_bt = champion_engine_v19(result_bt, accuracy_df_bt, top_each=10, top_n=40)
                ai_nums = get_ranked_no_list_for_backtest(decision_df_bt, limit=15)
            except Exception:
                ai_nums = get_ranked_no_list_for_backtest(result_bt.get("hybrid_all", pd.DataFrame()), limit=15)

            # Build Anchor Cluster from 4 model utama.
            model_stat = get_ranked_no_list_for_backtest(result_bt.get("stat", pd.DataFrame()), limit=10)
            model_position = get_ranked_no_list_for_backtest(result_bt.get("position", pd.DataFrame()), limit=10)
            model_pair = get_ranked_no_list_for_backtest(result_bt.get("pair", pd.DataFrame()), limit=10)
            model_nodouble = get_ranked_no_list_for_backtest(result_bt.get("theory", pd.DataFrame()), limit=20)

            acc_sources = [
                ("Statistik", model_stat),
                ("Peralihan", model_position),
                ("Pasangan", model_pair),
                ("No Double", model_nodouble),
            ]
            acc_df_bt = build_anchor_cluster_convergence_v30(acc_sources, top_families=10)
            anchor_families = acc_df_bt["Family"].astype(str).tolist() if acc_df_bt is not None and not acc_df_bt.empty and "Family" in acc_df_bt.columns else []

            result_pairs = list(dict.fromkeys(get_pairs([first, second, third])))

            # Pair Assist full dari Anchor, kemudian Density.
            pair_df_bt, _ = build_pair_assist_all_anchor_safe_v30(anchor_families, result_pairs)
            density_df_bt, _ = build_anchor_density_signal_v31(pair_df_bt, min_support=2, top_n=30)
            density_nums = density_df_bt["No"].astype(str).tolist() if density_df_bt is not None and not density_df_bt.empty else []

            # Density Overlap 3D dengan AI candidates.
            overlap_nums = []
            overlap_pairs = []
            for dn in density_nums:
                for an in ai_nums:
                    if overlap_count_4d(an, dn) >= 3:
                        if dn not in overlap_nums:
                            overlap_nums.append(dn)
                        overlap_pairs.append(f"{an} ↔ {dn}")
                        break

            # Pair Assist daripada Density sahaja.
            density_pair_df, _ = build_pair_assist_all_anchor_safe_v30(overlap_nums, result_pairs)

            density_pair_nums = []
            if density_pair_df is not None and not density_pair_df.empty:
                for _, r in density_pair_df.iterrows():
                    density_pair_nums.extend(_split_family_text_to_list(r.get("New Family", "")))
            density_pair_nums = list(dict.fromkeys(density_pair_nums))

            density_pair_fams = set(family4(n) for n in density_pair_nums)

            if has_next_result:
                actual_nums = [pad4(actual["first"]), pad4(actual["second"]), pad4(actual["third"])]
                actual_fams = [family4(n) for n in actual_nums]
                hit_nums = [actual_nums[i] for i, f in enumerate(actual_fams) if f in density_pair_fams]
                hit_status = "YES" if hit_nums else "NO"
                next_draw = str(actual.get("draw_no", idx + 1))
                next_result = " / ".join(actual_nums)
                hit_number = " / ".join(hit_nums)
            else:
                hit_status = "PENDING"
                next_draw = ""
                next_result = "Belum ada next draw"
                hit_number = ""

            rows.append({
                "Source Draw": str(source.get("draw_no", idx)),
                "Source Result": f"{first} / {second} / {third}",
                "Next Draw": next_draw,
                "Next Result": next_result,
                "AI Candidates": " / ".join(ai_nums),
                "Density Overlap Count": len(overlap_nums),
                "Density Overlap List": " / ".join(overlap_nums),
                "AI ↔ Density Match": " / ".join(overlap_pairs[:30]),
                "Pair Assist From Density Count": len(density_pair_nums),
                "Hit": hit_status,
                "Hit Number": hit_number,
            })

        except Exception as e:
            rows.append({
                "Source Draw": str(h.iloc[idx].get("draw_no", idx)) if idx < len(h) else "",
                "Error": str(e),
            })

    detail_df = pd.DataFrame(rows)

    if detail_df.empty:
        return pd.DataFrame(), detail_df

    valid = detail_df[detail_df.get("Hit", "").astype(str).isin(["YES", "NO"])].copy()
    pending = detail_df[detail_df.get("Hit", "").astype(str).eq("PENDING")].copy()
    total = len(valid)
    yes = int(valid["Hit"].eq("YES").sum()) if total else 0
    no = int(valid["Hit"].eq("NO").sum()) if total else 0

    summary_df = pd.DataFrame([
        {"Metric": "Tested source draws", "Value": total},
        {"Metric": "Pending latest draw", "Value": len(pending)},
        {"Metric": "YES", "Value": yes},
        {"Metric": "NO", "Value": no},
        {"Metric": "Hit Rate %", "Value": round((yes / total) * 100, 1) if total else 0},
        {"Metric": "Average Density Overlap Count", "Value": round(valid["Density Overlap Count"].mean(), 1) if total and "Density Overlap Count" in valid.columns else 0},
        {"Metric": "Average Pair Assist From Density Count", "Value": round(valid["Pair Assist From Density Count"].mean(), 1) if total and "Pair Assist From Density Count" in valid.columns else 0},
    ])

    return summary_df, detail_df


@st.cache_data(show_spinner=False)
def run_backtest_bridge_dde_lite_v31_24_5(history_df, test_draws=30):
    """Backtest Bridge V1 + V2 + V2 Ranker sahaja; DDE dikeluarkan."""
    import time
    t0 = time.perf_counter()
    if history_df is None or history_df.empty or len(history_df) < 30:
        return pd.DataFrame(), pd.DataFrame()
    h = history_df.copy().reset_index(drop=True)
    for col in ("first", "second", "third"):
        h[col] = h[col].apply(pad4)
    latest_idx = len(h) - 1
    count = max(1, min(int(test_draws), latest_idx - 20))
    start_idx = max(20, latest_idx - count + 1)
    rows = []
    try:
        v2_formula_bt = build_bridge_v2_formula_reliability(h.iloc[:start_idx + 1], lookback=300)
    except Exception:
        v2_formula_bt = {}
    # V1 hanya confirmation kecil dalam Combined audit; formula-history V1 yang
    # mahal tidak dibina semula untuk batch backtest.
    v1_formula_bt = {}
    for idx in range(start_idx, latest_idx + 1):
        try:
            source = h.iloc[idx]
            hist_available = h.iloc[:idx + 1]
            first, second, third = (pad4(source[c]) for c in ("first", "second", "third"))
            result_pairs = list(dict.fromkeys(get_pairs([first, second, third])))

            _, bridge_df_bt, _ = build_bridge_model_v31_9(first, second, third)
            bridge_list = bridge_df_bt["No"].astype(str).tolist() if not bridge_df_bt.empty else []
            bridge_fams = {family4(x) for x in bridge_list}
            _, bridge_v2_df_bt, _ = build_bridge_engine_v2_pair_double_digit(first, second, third)
            bridge_v2_list = bridge_v2_df_bt["No"].astype(str).tolist() if not bridge_v2_df_bt.empty else []
            bridge_v2_fams = {family4(x) for x in bridge_v2_list}
            bridge_v2_missing_fams = set(bridge_v2_df_bt[bridge_v2_df_bt["Mode"].str.contains("2 Missing", regex=False)]["Family"].astype(str)) if not bridge_v2_df_bt.empty else set()
            bridge_v2_existing_fams = set(bridge_v2_df_bt[bridge_v2_df_bt["Mode"].str.contains("2 Existing", regex=False)]["Family"].astype(str)) if not bridge_v2_df_bt.empty else set()

            generated = generate(hist_available, first, second, third)
            sources = [
                ("Statistik", get_ranked_no_list_for_backtest(generated.get("stat", pd.DataFrame()), 10)),
                ("Peralihan", get_ranked_no_list_for_backtest(generated.get("position", pd.DataFrame()), 10)),
                ("Pasangan", get_ranked_no_list_for_backtest(generated.get("pair", pd.DataFrame()), 10)),
                ("No Double", get_ranked_no_list_for_backtest(generated.get("theory", pd.DataFrame()), 20)),
            ]
            anchor_df = build_anchor_cluster_convergence_v30(sources, top_families=10)
            anchors = anchor_df["Family"].astype(str).tolist() if not anchor_df.empty else []
            pair_df, _ = build_pair_assist_all_anchor_safe_v30(anchors, result_pairs)
            density_df, _ = build_anchor_density_signal_v31(pair_df, min_support=2, top_n=30)
            v1_rank_df, _ = build_bridge_family_ranker_v31_24(
                bridge_df_bt, model_sources=sources, ai_nums=[], anchor_df=anchor_df,
                density_df=density_df, full_support={}, formula_reliability=v1_formula_bt, top_n=10,
            )
            v1_rank_df = promote_v1_genealogy_corrected_v31_26(v1_rank_df, top_n=10)
            v1_conv_list = v1_rank_df.sort_values("Conviction Rank")["Family"].astype(str).tolist() if not v1_rank_df.empty else []
            v1_bal_list = v1_rank_df.sort_values("Balanced Rank")["Family"].astype(str).tolist() if not v1_rank_df.empty else []
            v1_conv_map = {f: i + 1 for i, f in enumerate(v1_conv_list)}
            v1_bal_map = {f: i + 1 for i, f in enumerate(v1_bal_list)}
            v1_audit_maps = {}
            for profile in ("genealogy", "genealogy_consensus", "genealogy_convergence", "corrected"):
                audit_df = rerank_bridge_v1_corrected_v31_26(v1_rank_df, profile=profile, top_n=10)
                conv = audit_df.sort_values("Corrected Rank")["Family"].astype(str).tolist() if not audit_df.empty else []
                bal = audit_df.sort_values("Corrected Balanced Rank")["Family"].astype(str).tolist() if not audit_df.empty else []
                v1_audit_maps[profile] = (
                    {f: i + 1 for i, f in enumerate(conv)},
                    {f: i + 1 for i, f in enumerate(bal)},
                )
            v2_rank_df, _ = build_bridge_v2_family_ranker(
                bridge_v2_df_bt, bridge_v1_df=bridge_df_bt, model_sources=sources,
                anchor_df=anchor_df, density_df=density_df, formula_reliability=v2_formula_bt, top_n=10,
            )
            v2_conv_list = v2_rank_df.sort_values("Conviction Rank")["Family"].astype(str).tolist() if not v2_rank_df.empty else []
            v2_bal_list = v2_rank_df.sort_values("Balanced Rank")["Family"].astype(str).tolist() if not v2_rank_df.empty else []
            v2_unique_list = v2_rank_df[v2_rank_df["V2 Unique"]].sort_values("Unique Rank")["Family"].astype(str).tolist() if not v2_rank_df.empty else []
            v2_conv_map = {f: i + 1 for i, f in enumerate(v2_conv_list)}
            v2_bal_map = {f: i + 1 for i, f in enumerate(v2_bal_list)}
            v2_unique_map = {f: i + 1 for i, f in enumerate(v2_unique_list)}
            combined_df, _ = build_combined_family_ranker_v1_v2(v1_rank_df, v2_rank_df, top_n=10)
            combined_list = combined_df["Family"].astype(str).tolist() if not combined_df.empty else []
            combined_map = {f: i + 1 for i, f in enumerate(combined_list)}

            has_next = idx + 1 < len(h)
            if has_next:
                nxt = h.iloc[idx + 1]
                actual_nums = [pad4(nxt[c]) for c in ("first", "second", "third")]
                actual_fams = [family4(x) for x in actual_nums]
                bridge_hits = [n for n, fam in zip(actual_nums, actual_fams) if fam in bridge_fams]
                bridge_v2_hits = [n for n, fam in zip(actual_nums, actual_fams) if fam in bridge_v2_fams]
                bridge_v2_missing_hits = [n for n, fam in zip(actual_nums, actual_fams) if fam in bridge_v2_missing_fams]
                bridge_v2_existing_hits = [n for n, fam in zip(actual_nums, actual_fams) if fam in bridge_v2_existing_fams]
                v2_conv_ranks = [v2_conv_map[fam] for fam in actual_fams if fam in v2_conv_map]
                v2_bal_ranks = [v2_bal_map[fam] for fam in actual_fams if fam in v2_bal_map]
                v2_unique_ranks = [v2_unique_map[fam] for fam in actual_fams if fam in v2_unique_map]
                v2_rank_top3 = "YES" if v2_conv_ranks and min(v2_conv_ranks) <= 3 else "NO"
                v2_rank_top5 = "YES" if v2_conv_ranks and min(v2_conv_ranks) <= 5 else "NO"
                v2_rank_bal10 = "YES" if v2_bal_ranks and min(v2_bal_ranks) <= 10 else "NO"
                v2_rank_unique10 = "YES" if v2_unique_ranks and min(v2_unique_ranks) <= 10 else "NO"
                v2_rank_best = min(v2_conv_ranks) if v2_conv_ranks else ""
                v1_conv_ranks = [v1_conv_map[fam] for fam in actual_fams if fam in v1_conv_map]
                v1_bal_ranks = [v1_bal_map[fam] for fam in actual_fams if fam in v1_bal_map]
                v1_top3 = "YES" if v1_conv_ranks and min(v1_conv_ranks) <= 3 else "NO"
                v1_top5 = "YES" if v1_conv_ranks and min(v1_conv_ranks) <= 5 else "NO"
                v1_bal10 = "YES" if v1_bal_ranks and min(v1_bal_ranks) <= 10 else "NO"
                v1_audit_hits = {}
                for profile, (conv_map, bal_map) in v1_audit_maps.items():
                    cr = [conv_map[f] for f in actual_fams if f in conv_map]
                    br = [bal_map[f] for f in actual_fams if f in bal_map]
                    v1_audit_hits[profile] = (
                        "YES" if cr and min(cr) <= 3 else "NO",
                        "YES" if cr and min(cr) <= 5 else "NO",
                        "YES" if cr and min(cr) <= 10 else "NO",
                        "YES" if br and min(br) <= 10 else "NO",
                    )
                combined_ranks = [combined_map[fam] for fam in actual_fams if fam in combined_map]
                combined_top3 = "YES" if combined_ranks and min(combined_ranks) <= 3 else "NO"
                combined_top5 = "YES" if combined_ranks and min(combined_ranks) <= 5 else "NO"
                combined_top10 = "YES" if combined_ranks and min(combined_ranks) <= 10 else "NO"
                combined_best = min(combined_ranks) if combined_ranks else ""
                next_draw = str(nxt.get("draw_no", ""))
                next_result = " / ".join(actual_nums)
                bridge_status = "YES" if bridge_hits else "NO"
                bridge_v2_status = "YES" if bridge_v2_hits else "NO"
                bridge_v2_missing_status = "YES" if bridge_v2_missing_hits else "NO"
                bridge_v2_existing_status = "YES" if bridge_v2_existing_hits else "NO"
                union_hits = list(dict.fromkeys(bridge_hits + bridge_v2_hits))
                union_status = "YES" if union_hits else "NO"
            else:
                next_draw, next_result = "", "Belum ada next draw"
                bridge_hits, bridge_v2_hits, bridge_v2_missing_hits, bridge_v2_existing_hits, union_hits = [], [], [], [], []
                bridge_status = bridge_v2_status = bridge_v2_missing_status = bridge_v2_existing_status = union_status = "PENDING"
                v2_rank_top3 = v2_rank_top5 = v2_rank_bal10 = v2_rank_unique10 = "PENDING"
                v2_rank_best = ""
                v1_top3 = v1_top5 = v1_bal10 = "PENDING"
                v1_audit_hits = {p: ("PENDING", "PENDING", "PENDING", "PENDING") for p in v1_audit_maps}
                combined_top3 = combined_top5 = combined_top10 = "PENDING"
                combined_best = ""
            rows.append({
                "Source Draw": str(source.get("draw_no", idx)),
                "Source Result": f"{first} / {second} / {third}",
                "Next Draw": next_draw, "Next Result": next_result,
                "Bridge Count": len(bridge_list), "Bridge List": " / ".join(bridge_list),
                "Bridge Hit": bridge_status, "Bridge Hit Number": " / ".join(bridge_hits),
                "Bridge V2 Count": len(bridge_v2_list), "Bridge V2 List": " / ".join(bridge_v2_list),
                "Bridge V2 Hit": bridge_v2_status, "Bridge V2 Hit Number": " / ".join(bridge_v2_hits),
                "Bridge V2 2-Missing Hit": bridge_v2_missing_status,
                "Bridge V2 2-Missing Hit Number": " / ".join(bridge_v2_missing_hits),
                "Bridge V2 2-Existing Hit": bridge_v2_existing_status,
                "Bridge V2 2-Existing Hit Number": " / ".join(bridge_v2_existing_hits),
                "V2 Ranker Top 5": " / ".join(v2_conv_list[:5]),
                "V2 Ranker Balanced Top 10": " / ".join(v2_bal_list[:10]),
                "V2 Ranker Unique Top 10": " / ".join(v2_unique_list[:10]),
                "V2 Ranker Conviction Top3 Hit": v2_rank_top3,
                "V2 Ranker Conviction Top5 Hit": v2_rank_top5,
                "V2 Ranker Balanced Top10 Hit": v2_rank_bal10,
                "V2 Ranker Unique Top10 Hit": v2_rank_unique10,
                "V2 Ranker Best Rank": str(v2_rank_best) if v2_rank_best != "" else "",
                "V1 Ranker Conviction Top3 Hit": v1_top3,
                "V1 Ranker Conviction Top5 Hit": v1_top5,
                "V1 Ranker Balanced Top10 Hit": v1_bal10,
                **{
                    f"V1 Audit {profile} Top{cutoff} Hit": v1_audit_hits[profile][pos]
                    for profile in v1_audit_hits
                    for pos, cutoff in enumerate((3, 5, "10 Conviction"))
                },
                **{f"V1 Audit {profile} Top10 Balanced Hit": v1_audit_hits[profile][3] for profile in v1_audit_hits},
                "Combined Ranker Top 10": " / ".join(combined_list[:10]),
                "Combined Ranker Top3 Hit": combined_top3,
                "Combined Ranker Top5 Hit": combined_top5,
                "Combined Ranker Top10 Hit": combined_top10,
                "Combined Ranker Best Rank": str(combined_best) if combined_best != "" else "",
                "Hit": union_status, "Hit Number": " / ".join(union_hits),
            })
        except Exception as exc:
            rows.append({"Source Draw": str(h.iloc[idx].get("draw_no", idx)), "Hit": "ERROR", "Error": str(exc)})
    detail = pd.DataFrame(rows)
    valid = detail[detail.get("Hit", pd.Series(dtype=str)).astype(str).isin(["YES", "NO"])]
    total = len(valid)
    bridge_yes = int(valid.get("Bridge Hit", pd.Series(dtype=str)).eq("YES").sum())
    bridge_v2_yes = int(valid.get("Bridge V2 Hit", pd.Series(dtype=str)).eq("YES").sum())
    bridge_v2_missing_yes = int(valid.get("Bridge V2 2-Missing Hit", pd.Series(dtype=str)).eq("YES").sum())
    bridge_v2_existing_yes = int(valid.get("Bridge V2 2-Existing Hit", pd.Series(dtype=str)).eq("YES").sum())
    bridge_union_yes = int((
        valid.get("Bridge Hit", pd.Series("", index=valid.index)).astype(str).eq("YES")
        | valid.get("Bridge V2 Hit", pd.Series("", index=valid.index)).astype(str).eq("YES")
    ).sum())
    v2_top3_yes = int(valid.get("V2 Ranker Conviction Top3 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v2_top5_yes = int(valid.get("V2 Ranker Conviction Top5 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v2_bal10_yes = int(valid.get("V2 Ranker Balanced Top10 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v2_unique10_yes = int(valid.get("V2 Ranker Unique Top10 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v1_top3_yes = int(valid.get("V1 Ranker Conviction Top3 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v1_top5_yes = int(valid.get("V1 Ranker Conviction Top5 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v1_bal10_yes = int(valid.get("V1 Ranker Balanced Top10 Hit", pd.Series(dtype=str)).eq("YES").sum())
    combined_top3_yes = int(valid.get("Combined Ranker Top3 Hit", pd.Series(dtype=str)).eq("YES").sum())
    combined_top5_yes = int(valid.get("Combined Ranker Top5 Hit", pd.Series(dtype=str)).eq("YES").sum())
    combined_top10_yes = int(valid.get("Combined Ranker Top10 Hit", pd.Series(dtype=str)).eq("YES").sum())
    v1_audit_totals = {
        (profile, cutoff): int(valid.get(
            f"V1 Audit {profile} Top{cutoff} Hit", pd.Series(dtype=str)
        ).eq("YES").sum())
        for profile in ("genealogy", "genealogy_consensus", "genealogy_convergence", "corrected")
        for cutoff in (3, 5, "10 Conviction", "10 Balanced")
    }
    summary = pd.DataFrame([
        {"Metric": "Tested source draws", "Value": total},
        {"Metric": "Pending latest draw", "Value": int(detail.get("Hit", pd.Series(dtype=str)).eq("PENDING").sum())},
        {"Metric": "Bridge YES", "Value": bridge_yes},
        {"Metric": "Bridge Hit Rate %", "Value": round(bridge_yes / total * 100, 1) if total else 0},
        {"Metric": "Bridge V2 YES", "Value": bridge_v2_yes},
        {"Metric": "Bridge V2 Hit Rate %", "Value": round(bridge_v2_yes / total * 100, 1) if total else 0},
        {"Metric": "V2 2-Missing YES", "Value": bridge_v2_missing_yes},
        {"Metric": "V2 2-Existing YES", "Value": bridge_v2_existing_yes},
        {"Metric": "V2 Ranker Conviction Top 3", "Value": v2_top3_yes},
        {"Metric": "V2 Ranker Conviction Top 5", "Value": v2_top5_yes},
        {"Metric": "V2 Ranker Balanced Top 10", "Value": v2_bal10_yes},
        {"Metric": "V2 Ranker Unique Top 10", "Value": v2_unique10_yes},
        {"Metric": "V1 Ranker Conviction Top 3", "Value": v1_top3_yes},
        {"Metric": "V1 Ranker Conviction Top 5", "Value": v1_top5_yes},
        {"Metric": "V1 Ranker Balanced Top 10", "Value": v1_bal10_yes},
        *[
            {"Metric": f"V1 Corrected Audit {profile} Top {cutoff}", "Value": v1_audit_totals[(profile, cutoff)]}
            for profile in ("genealogy", "genealogy_consensus", "genealogy_convergence", "corrected")
            for cutoff in (3, 5, "10 Conviction", "10 Balanced")
        ],
        {"Metric": "Combined Ranker Top 3", "Value": combined_top3_yes},
        {"Metric": "Combined Ranker Top 5", "Value": combined_top5_yes},
        {"Metric": "Combined Ranker Top 10", "Value": combined_top10_yes},
        {"Metric": "Bridge V1 atau V2 Hit", "Value": bridge_union_yes},
        {"Metric": "Total Unique Hit Rate %", "Value": round(bridge_union_yes / total * 100, 1) if total else 0},
        {"Metric": "Elapsed Seconds", "Value": round(time.perf_counter() - t0, 2)},
    ])
    return summary, detail

def _first_existing_backtest_column(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def build_clean_backtest_quick_review(detail_df):
    """Paparan ringkas: keputusan draw serta hit Bridge V1, V2 dan V2 Ranker."""
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
    """Summary mesra pengguna yang hanya menilai Bridge dan DDE."""
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
    for label, col in [
        ("Combined Ranker Top 3", "Combined Ranker Top3 Hit"),
        ("Combined Ranker Top 5", "Combined Ranker Top5 Hit"),
        ("Combined Ranker Top 10", "Combined Ranker Top10 Hit"),
        ("V2 Ranker Conviction Top 3", "V2 Ranker Conviction Top3 Hit"),
        ("V2 Ranker Conviction Top 5", "V2 Ranker Conviction Top5 Hit"),
        ("V2 Ranker Balanced Top 10", "V2 Ranker Balanced Top10 Hit"),
        ("V2 Ranker Unique Top 10", "V2 Ranker Unique Top10 Hit"),
        ("Family Conviction Top 3", "Family Ranker Conviction Top3 Hit"),
        ("Family Conviction Top 5", "Family Ranker Conviction Top5 Hit"),
        ("Family Balanced Top 10", "Family Ranker Balanced Top10 Hit"),
    ]:
        if col in valid.columns:
            count = int(valid[col].astype(str).eq("YES").sum())
            rate = round((count / completed) * 100, 1) if completed else 0
            rows.append({"Metric": label, "Value": f"{count}/{completed} ({rate}%)"})
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
with st.expander("🧪 Backtest Bridge V1 + V2", expanded=False):
    st.caption("Semak hit Bridge V1, Bridge V2 dan V2 Family Ranker bagi setiap draw.")
    bt_col1, bt_col2 = st.columns(2)
    with bt_col1:
        bt_draws = st.selectbox("Jumlah source draw untuk test", [10, 20, 30, 50, 100], index=2, key="simple_bt_draws_v31_6")
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
            st.subheader("Summary Bridge + DDE")
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
    st.subheader("🎲 Generate Analisis Family")
    st.caption("Keputusan terbaru telah diisi secara automatik. Tekan Generate untuk analisis Bridge dan shortlist family.")
    c1, c2, c3 = st.columns(3)
    first = c1.text_input("1st Prize", value=last["first"], max_chars=4)
    second = c2.text_input("2nd Prize", value=last["second"], max_chars=4)
    third = c3.text_input("3rd Prize", value=last["third"], max_chars=4)
    submitted = st.form_submit_button("Generate")

if submitted:
    result = generate(st.session_state.history, first, second, third)
    stability_df = prediction_stability_index(
        st.session_state.history,
        first,
        second,
        third,
        rounds=5,
        top_n=20,
    )
    result["stability_tracker"] = stability_df
    result["hybrid_all"] = add_stability_to_hybrid(result["hybrid_all"], stability_df)
    result["hybrid"] = result["hybrid_all"].head(20).copy()
    accuracy_df = model_accuracy_tracker(st.session_state.history, lookback=100)
    result["champion_v19"] = champion_engine_v19(result, accuracy_df, top_each=10, top_n=40)
    result["champion_v19_audit"] = champion_v19_audit(result["champion_v19"])
    result["consensus_boost_v19_1"] = consensus_boost_v19_1(result, result["champion_v19"], top_each=30, top_n=40)
    result["consensus_boost_audit_v19_1"] = consensus_boost_audit_v19_1(result["consensus_boost_v19_1"])

    result["breakdown"] = score_breakdown_table(
        result["hybrid_all"],
        result["stat"],
        result["position"],
        result["pair"],
        result["theory"],
    )
    st.success("Analisis family berjaya dijana.")

    top_n = 20

    decision_df = result["champion_v19"].copy()
    decision_df["No"] = decision_df["No"].astype(str).str.zfill(4)

    def rating_from_rank(rank):
        try:
            rank = int(rank)
        except Exception:
            rank = 99
        if rank <= 2:
            return "⭐⭐⭐⭐⭐"
        elif rank <= 5:
            return "⭐⭐⭐⭐"
        elif rank <= 10:
            return "⭐⭐⭐"
        elif rank <= 15:
            return "⭐⭐"
        return "⭐"

    decision_df["Rating"] = decision_df["Rank"].apply(rating_from_rank)
    decision_df["Confidence %"] = decision_df["Confidence"].round(0).astype(int).astype(str) + "%"
    decision_simple = decision_df[["No", "Rating"]].copy()

    ai_pick = decision_df.iloc[0]
    ai_pick_no = str(ai_pick["No"]).zfill(4)
    ai_pick_rating = ai_pick["Rating"]
    ai_pick_conf = str(int(round(float(ai_pick["Confidence"]), 0))) + "%"

    # -----------------------------
    # V27: Core Prediction Models moved up
    # -----------------------------
    # V31.24.2.1: expander tidak mencetuskan rerun seperti toggle/checkbox.
    with st.expander("🔬 Signal Lab (audit teknikal)", expanded=False):
        st.caption("Empat model ini ialah signal backend, bukan shortlist nombor utama.")
        signal_tabs = st.tabs(["Statistik", "Peralihan", "Pasangan", "No Double"])
        with signal_tabs[0]:
            st.dataframe(result["stat"], hide_index=True, use_container_width=True)
        with signal_tabs[1]:
            st.dataframe(result["position"], hide_index=True, use_container_width=True)
        with signal_tabs[2]:
            st.dataframe(result["pair"], hide_index=True, use_container_width=True)
        with signal_tabs[3]:
            st.dataframe(result["theory"], hide_index=True, use_container_width=True)

    # Audit tambahan kekal tersembunyi daripada aliran utama.
    show_signal_lab = False

    def model_no_list(df, limit=10):
        try:
            if df is None or df.empty or "No" not in df.columns:
                return []

            copy_df = df.copy()

            # Pastikan copy ikut susunan Rank yang dipaparkan dalam jadual.
            if "Rank" in copy_df.columns:
                try:
                    copy_df["Rank"] = pd.to_numeric(copy_df["Rank"], errors="coerce")
                    copy_df = copy_df.sort_values("Rank", ascending=True)
                except Exception:
                    pass

            nums = copy_df["No"].astype(str).head(limit).tolist()
            return [pad4(x) for x in nums]
        except Exception:
            return []

    # Copy ikut data jadual yang sedang dipaparkan, bukan senarai lama/cache.
    model_stat_list = model_no_list(result["stat"], limit=10)
    model_position_list = model_no_list(result["position"], limit=10)
    model_pair_list = model_no_list(result["pair"], limit=10)
    model_nodouble_list = model_no_list(result["theory"], limit=20)

    model_share_text = f"""🎯 Rumah A Predictor - Ramalan Model

📊 Model Statistik:
{' / '.join(model_stat_list)}

🔁 Model Peralihan Posisi:
{' / '.join(model_position_list)}

🔗 Model Pasangan:
{' / '.join(model_pair_list)}

🔢 Model No Double:
{' / '.join(model_nodouble_list[:10])}
{' / '.join(model_nodouble_list[10:20])}
"""

    if show_signal_lab:
        with st.expander("📋 Copy output mentah Signal Lab", expanded=False):
            copy_button_clean("📋 Copy Semua Signal", model_share_text, "all_models_fixed")
            st.text_area("Signal untuk audit", value=model_share_text, height=220, label_visibility="collapsed")



    # -----------------------------
    # POLISHED UI: AI Decision terus selepas Copy Ramalan Model
    # -----------------------------
    top3_df = decision_simple.iloc[0:3].copy()
    top3_list = top3_df["No"].tolist()
    top3_text = " / ".join(top3_list)

    strong_extra = decision_simple.iloc[3:10].copy()
    backup_pool = decision_simple.iloc[10:15].copy()

    strong_extra_list = strong_extra["No"].tolist()
    backup_list = backup_pool["No"].tolist()
    strong_text = " / ".join(strong_extra_list)
    backup_text = " / ".join(backup_list)

    # V31.24.2: Legacy AI/Champion dikira untuk compatibility audit sahaja.
    # Ia tidak dipaparkan dan tidak lagi menjadi input shortlist utama.
    share_text = f"""🎯 Rumah A Predictor

🔥 AI Pick:
{ai_pick_no}

🥇 Top 3:
{top3_text}

⭐ Strong Buy:
{strong_text}

🎯 Backup:
{backup_text}
"""
    top3_share = top3_text

    # -----------------------------
    # Bridge Model - Pair Order
    # -----------------------------
    st.subheader("🧪 Bridge Model - Pair Order")
    st.caption("Pair depan/tengah/belakang + 1 missing digit + 1 existing digit. Duplicate family dibuang.")

    bridge_df = pd.DataFrame()
    bridge_pair_df = pd.DataFrame()
    try:
        bridge_pair_df, bridge_df, bridge_text = build_bridge_model_v31_9(first, second, third)
        if bridge_df.empty:
            st.info("Bridge Model belum menghasilkan output.")
        else:
            st.caption(f"Jumlah Bridge Family: {len(bridge_df)}")
            copy_button_clean("📋 Copy Bridge Model", bridge_text, "bridge_model_v31_9")
            with st.expander("Lihat Bridge Model", expanded=False):
                st.markdown("**Base Pair**")
                st.dataframe(bridge_pair_df, hide_index=True, use_container_width=True)
                st.markdown("**Bridge Families**")
                st.dataframe(bridge_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Model belum dapat dipaparkan: {e}")

    # -----------------------------
    # Bridge Engine V2 - Pair + 2D Missing / Pair + 2D Existing
    # -----------------------------
    st.subheader("🧪 Bridge Engine V2 - Double Digit")
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
                f"Jumlah unique family: {len(bridge_v2_df)} | "
                f"2 Missing: {v2_missing_count} | 2 Existing: {v2_existing_count}"
            )
            copy_button_clean("📋 Copy Bridge Engine V2", bridge_v2_text, "bridge_engine_v2_double_digit")
            with st.expander("Lihat Bridge Engine V2", expanded=False):
                st.dataframe(bridge_v2_df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.warning(f"Bridge Engine V2 belum dapat dipaparkan: {e}")

    # -----------------------------
    # Pemboleh ubah signal (backend sahaja)
    # -----------------------------
    try:
        signal_stat_nums = get_no_list_for_signal(result["stat"], limit=10)
        signal_position_nums = get_no_list_for_signal(result["position"], limit=10)
        signal_pair_nums = get_no_list_for_signal(result["pair"], limit=10)
        signal_nodouble_nums = get_no_list_for_signal(result["theory"], limit=20)

        digit_signal_df, pair_signal_df, number_signal_df = build_signal_strength(
            signal_stat_nums,
            signal_position_nums,
            signal_pair_nums,
            signal_nodouble_nums
        )
    except Exception:
        signal_stat_nums = []
        signal_position_nums = []
        signal_pair_nums = []
        signal_nodouble_nums = []
        digit_signal_df = pd.DataFrame()
        pair_signal_df = pd.DataFrame()
        number_signal_df = pd.DataFrame()

    # -----------------------------
    # Anchor Cluster Convergence
    # -----------------------------
    if show_signal_lab:
        st.subheader("🧬 Anchor Cluster Convergence")
        st.caption("Anchor 2D → Cluster → Hidden Family.")

    try:
        acc_sources = [
            ("Statistik", signal_stat_nums),
            ("Peralihan", signal_position_nums),
            ("Pasangan", signal_pair_nums),
            ("No Double", signal_nodouble_nums),
        ]

        acc_df = build_anchor_cluster_convergence_v30(
            acc_sources,
            top_families=10,
        )

        if not acc_df.empty:
            anchor_numbers = [pad4(x) for x in acc_df["Family"].astype(str).tolist()]
            anchor_numbers = list(dict.fromkeys(anchor_numbers))[:10]
            anchor_copy_text = (
                "🧬 Rumah A Predictor - Anchor Cluster Convergence\n\n"
                + " / ".join(anchor_numbers)
            )
            if show_signal_lab:
                copy_button_clean("📋 Copy Anchor Cluster", anchor_copy_text, "anchor_cluster_convergence")
                with st.expander("Lihat Detail Anchor Cluster Convergence", expanded=False):
                    st.dataframe(acc_df, hide_index=True, use_container_width=True)

    except Exception as e:
        acc_df = pd.DataFrame()
        st.warning(f"Anchor Cluster Convergence belum dapat dipaparkan: {e}")

    # -----------------------------
    # Pair Assist + Anchor Density + Pair Pick (backend sahaja)
    # -----------------------------
    try:
        if acc_df is not None and not acc_df.empty and "Family" in acc_df.columns:
            _anchor_families_safe = acc_df["Family"].astype(str).tolist()
        else:
            _anchor_families_safe = []

        _result_pairs_safe = list(dict.fromkeys(get_pairs([pad4(first), pad4(second), pad4(third)])))
        pair_assist_safe_df, pair_assist_safe_lines = build_pair_assist_all_anchor_safe_v30(
            _anchor_families_safe,
            _result_pairs_safe
        )

        if pair_assist_safe_df is not None and not pair_assist_safe_df.empty:
            density_df, density_text = build_anchor_density_signal_v31(
                pair_assist_safe_df,
                min_support=2,
                top_n=30,
            )
        else:
            density_df, density_text = pd.DataFrame(), ""

        pair_pick_df = build_pair_assist_pick_engine_v30(
            pair_assist_safe_df if pair_assist_safe_df is not None else pd.DataFrame(),
            _result_pairs_safe,
            anchor_families=_anchor_families_safe,
            top_n=20,
        )
    except Exception:
        pair_assist_safe_df = pd.DataFrame()
        pair_assist_safe_lines = []
        density_df = pd.DataFrame()
        density_text = ""
        pair_pick_df = pd.DataFrame()
        _result_pairs_safe = []

    # -----------------------------
    # Density Decision Engine - paparan ringkas, copy semua nombor
    # -----------------------------
    if show_signal_lab:
        st.subheader("🎯 Density Confirmation Audit")

    try:
        # V31.24.2: Anchor families menggantikan Legacy AI Pick supaya tiada circular scoring.
        _ai_for_decision = anchor_numbers if "anchor_numbers" in locals() else []

        density_decision_df, _density_decision_text = build_density_decision_engine_v31_8(
            density_df if density_df is not None else pd.DataFrame(),
            _ai_for_decision,
            pair_pick_df=pair_pick_df if pair_pick_df is not None else pd.DataFrame(),
            top_n=5,
        )

        if not density_decision_df.empty:
            number_col = "No" if "No" in density_decision_df.columns else "Family"
            all_density_numbers = [pad4(x) for x in density_decision_df[number_col].astype(str).tolist()]
            all_density_numbers = list(dict.fromkeys(all_density_numbers))
            density_lines = [
                " / ".join(all_density_numbers[i:i + 10])
                for i in range(0, len(all_density_numbers), 10)
            ]
            density_copy_text = (
                "🎯 Rumah A Predictor - Density Decision Engine\n"
                + f"Total Numbers: {len(all_density_numbers)}\n\n"
                + "\n".join(density_lines)
            )

            if show_signal_lab:
                st.code("\n".join(density_lines), language=None)
                copy_button_clean("📋 Copy Semua Nombor", density_copy_text, "density_decision_copy_all_numbers")
                with st.expander("Lihat Detail Density Confirmation", expanded=False):
                    st.dataframe(density_decision_df, hide_index=True, use_container_width=True)

    except Exception as e:
        density_decision_df = pd.DataFrame()
        st.warning(f"Density Decision Engine belum dapat dipaparkan: {e}")

    # -----------------------------
    # V31.24: Bridge Family Ranker V1
    # -----------------------------
    st.subheader("🧬 Bridge Family Ranker V1 Corrected — Primary Shortlist")
    st.caption("Shortlist audit-safe: Genealogy Bridge V1 sahaja. Formula History, model lama dan forced-balanced tidak mempengaruhi ranking.")

    try:
        family_model_sources = [
            ("Statistik", signal_stat_nums),
            ("Peralihan", signal_position_nums),
            ("Pasangan", signal_pair_nums),
            ("No Double", signal_nodouble_nums),
        ]
        family_ai_nums = []  # Legacy AI/Champion dikeluarkan daripada ranking V31.24.2.
        bridge_family_rank_df, bridge_family_rank_text = build_bridge_family_ranker_v31_24(
            bridge_df,
            model_sources=family_model_sources,
            ai_nums=family_ai_nums,
            anchor_df=acc_df if "acc_df" in locals() else pd.DataFrame(),
            density_df=density_decision_df if density_decision_df is not None else pd.DataFrame(),
            full_support={},
            formula_reliability={},
            top_n=10,
        )
        bridge_family_rank_df = promote_v1_genealogy_corrected_v31_26(bridge_family_rank_df, top_n=10)
        if not bridge_family_rank_df.empty:
            _v1c = bridge_family_rank_df.sort_values("Conviction Rank")["Family"].astype(str).tolist()
            bridge_family_rank_text = (
                "🧬 Rumah A Predictor - Bridge Family Ranker V1 Corrected\n\n"
                + "Top 3 Corrected:\n" + " / ".join(_v1c[:3]) + "\n\n"
                + "Top 5 Corrected:\n" + " / ".join(_v1c[:5]) + "\n\n"
                + "Top 10 Corrected:\n" + " / ".join(_v1c[:10])
            )

        if bridge_family_rank_df.empty:
            st.info("Bridge Family Ranker belum mempunyai calon.")
        else:
            conviction_view = bridge_family_rank_df.sort_values("Conviction Rank")
            balanced_view = bridge_family_rank_df.sort_values("Balanced Rank")
            top3_family = conviction_view.head(3)["Family"].astype(str).tolist()
            top5_family = conviction_view.head(5)["Family"].astype(str).tolist()
            top10_family = balanced_view.head(10)["Family"].astype(str).tolist()
            st.markdown(
                f"**Top 3 Conviction:** {' / '.join(top3_family)}  \n"
                f"**Top 5 Conviction:** {' / '.join(top5_family)}  \n"
                f"**Top 10 Corrected:** {' / '.join(top10_family)}"
            )
            copy_button_clean("📋 Copy Family Shortlist", bridge_family_rank_text, "bridge_family_ranker_v31_24")
            with st.expander("Lihat sebab dan markah Family Ranker", expanded=False):
                st.dataframe(bridge_family_rank_df.head(20), hide_index=True, use_container_width=True)
    except Exception as e:
        bridge_family_rank_df = pd.DataFrame()
        st.warning(f"Bridge Family Ranker belum dapat dipaparkan: {e}")

    # -----------------------------
    # Bridge V2 Family Ranker - independent
    # -----------------------------
    st.subheader("🧬 Bridge V2 Family Ranker — Secondary Coverage")
    st.caption("Shortlist tambahan: utamakan V2 Unique untuk family yang tidak muncul secara exact dalam V1.")
    try:
        v2_model_sources = [
            ("Statistik", signal_stat_nums), ("Peralihan", signal_position_nums),
            ("Pasangan", signal_pair_nums), ("No Double", signal_nodouble_nums),
        ]
        bridge_v2_rank_df, bridge_v2_rank_text = build_bridge_v2_family_ranker(
            bridge_v2_df, bridge_v1_df=bridge_df, model_sources=v2_model_sources,
            anchor_df=acc_df, density_df=density_decision_df,
            formula_reliability=build_bridge_v2_formula_reliability(st.session_state.history, lookback=800),
            top_n=10,
        )
        if bridge_v2_rank_df.empty:
            st.info("Bridge V2 Family Ranker belum mempunyai calon.")
        else:
            v2_conv = bridge_v2_rank_df.sort_values("Conviction Rank")
            v2_bal = bridge_v2_rank_df.sort_values("Balanced Rank")
            v2_unique = bridge_v2_rank_df[bridge_v2_rank_df["V2 Unique"]].sort_values("Unique Rank")
            st.markdown(
                f"**Top 3 Conviction:** {' / '.join(v2_conv.head(3)['Family'].tolist())}  \n"
                f"**Top 5 Conviction:** {' / '.join(v2_conv.head(5)['Family'].tolist())}  \n"
                f"**Top 10 Balanced:** {' / '.join(v2_bal.head(10)['Family'].tolist())}  \n"
                f"**Top 10 V2 Unique:** {' / '.join(v2_unique.head(10)['Family'].tolist())}"
            )
            copy_button_clean("📋 Copy Bridge V2 Family Shortlist", bridge_v2_rank_text, "bridge_v2_family_ranker")
            with st.expander("Lihat sebab dan markah Bridge V2 Ranker", expanded=False):
                st.dataframe(bridge_v2_rank_df.head(30), hide_index=True, use_container_width=True)
    except Exception as e:
        bridge_v2_rank_df = pd.DataFrame()
        st.warning(f"Bridge V2 Family Ranker belum dapat dipaparkan: {e}")

    st.subheader("🏆 Combined Family Ranker V1 + V2")
    st.caption("V2 menentukan shortlist; V1 Corrected Genealogy digunakan sebagai confirmation/tie-break tanpa dipaksa masuk.")
    try:
        combined_family_df, combined_family_text = build_combined_family_ranker_v1_v2(
            bridge_family_rank_df, bridge_v2_rank_df, top_n=10
        )
        if combined_family_df.empty:
            st.info("Combined Family Ranker belum mempunyai calon.")
        else:
            st.markdown(
                f"**Top 3 Combined:** {' / '.join(combined_family_df.head(3)['Family'].tolist())}  \n"
                f"**Top 5 Combined:** {' / '.join(combined_family_df.head(5)['Family'].tolist())}  \n"
                f"**Top 10 Combined:** {' / '.join(combined_family_df.head(10)['Family'].tolist())}"
            )
            copy_button_clean("📋 Copy Combined Family Shortlist", combined_family_text, "combined_family_ranker_v1_v2")
            with st.expander("Lihat sebab dan markah Combined Ranker", expanded=False):
                st.dataframe(combined_family_df.head(30), hide_index=True, use_container_width=True)
    except Exception as e:
        combined_family_df = pd.DataFrame()
        st.warning(f"Combined Family Ranker belum dapat dipaparkan: {e}")

    # -----------------------------
    # Pair Arrangement (backend sahaja untuk Result Chart Board)
    # -----------------------------
    try:
        pair_arr_df = build_pair_arrangement_engine_v30(
            pair_pick_df if pair_pick_df is not None else pd.DataFrame(),
            _result_pairs_safe,
            top_per_family=3,
        )
    except Exception:
        pair_arr_df = pd.DataFrame()

    hot_df = hot_digit_analysis(st.session_state.history, window=hot_window if "hot_window" in globals() else 30)
    cold_df = cold_digit_analysis(st.session_state.history, window=cold_window if "cold_window" in globals() else 100)

    report_inputs = {
        "1st": pad4(first),
        "2nd": pad4(second),
        "3rd": pad4(third),
        "Latest Draw No": str(st.session_state.history.iloc[-1]["draw_no"]),
        "Latest Draw Date": str(st.session_state.history.iloc[-1]["draw_date"]),
        "Top N": top_n,
    }




# === Result Chart Board V3 DATA-DRIVEN ===
def _tetris_placements_v31():
    bases = {
        "I": {(0, 0), (1, 0), (2, 0), (3, 0)},
        "L": {(0, 0), (1, 0), (2, 0), (2, 1)},
        "Z/S": {(0, 0), (0, 1), (1, 1), (1, 2)},
        "2x2": {(0, 0), (0, 1), (1, 0), (1, 1)},
        "T": {(0, 0), (0, 1), (0, 2), (1, 1)},
    }
    def norm(shape):
        mr = min(r for r, _ in shape); mc = min(c for _, c in shape)
        return frozenset((r - mr, c - mc) for r, c in shape)
    out = []
    for name, base in bases.items():
        variants = set()
        for reflected in (False, True):
            shape = {(r, -c) if reflected else (r, c) for r, c in base}
            for _ in range(4):
                shape = {(c, -r) for r, c in shape}
                variants.add(norm(shape))
        for shape in variants:
            height = max(r for r, _ in shape) + 1; width = max(c for _, c in shape) + 1
            for dr in range(5 - height):
                for dc in range(5 - width):
                    cells = tuple(sorted((r + dr, c + dc) for r, c in shape))
                    out.append((name, cells))
    return list(dict.fromkeys(out))


def _tetris_matches_v31(selected, target_families=None):
    target_families = set(target_families or [])
    exact, near = [], []
    for shape, cells in _tetris_placements_v31():
        no = "".join(selected[c][r] for r, c in cells)
        fam = family4(no)
        row = {"Shape": shape, "No": no, "Family": fam, "Cells": " / ".join(f"R{r+1}C{c+1}" for r, c in cells)}
        if fam in target_families:
            exact.append(row)
        elif target_families:
            best = max((overlap_count_4d(fam, target), target) for target in target_families)
            if best[0] == 3:
                row["Near Family"] = best[1]
                near.append(row)
    return pd.DataFrame(exact).drop_duplicates() if exact else pd.DataFrame(), pd.DataFrame(near).drop_duplicates() if near else pd.DataFrame()


def build_result_chart_board_v3(full_df, bridge_df=None, family_df=None, lookback=12):
    """Position board daripada frequency, prize weight, recency dan confirmation sebenar."""
    if full_df is None or full_df.empty:
        return "", pd.DataFrame(), {}
    df = full_df.copy()
    if "DrawNo" in df.columns:
        df["_draw_sort"] = pd.to_numeric(df["DrawNo"], errors="coerce")
        df = df.sort_values("_draw_sort")
    recent = df.tail(max(1, int(lookback))).reset_index(drop=True)
    score = [Counter() for _ in range(4)]
    latest_count = [Counter() for _ in range(4)]
    number_cols = [c for c in recent.columns if str(c) not in ("DrawNo", "DrawDate", "_draw_sort")]

    for age, (_, row) in enumerate(recent.iloc[::-1].iterrows()):
        recency_weight = 1.0 / (1.0 + age * 0.25)
        for col in number_cols:
            raw = row.get(col, "")
            try:
                if pd.isna(raw):
                    continue
            except Exception:
                pass
            no = pad4(raw)
            if len(no) != 4:
                continue
            prize_weight = 3.0 if str(col) in ("1stPrizeNo", "2ndPrizeNo", "3rdPrizeNo") else 1.0
            for pos, digit in enumerate(no):
                score[pos][digit] += prize_weight * recency_weight
                if age == 0:
                    latest_count[pos][digit] += 1

    bridge_pos = [Counter() for _ in range(4)]
    if bridge_df is not None and not bridge_df.empty and "No" in bridge_df.columns:
        for no in bridge_df["No"].astype(str).tolist():
            s = pad4(no)
            for pos, digit in enumerate(s):
                bridge_pos[pos][digit] += 1

    family_digits = Counter()
    if family_df is not None and not family_df.empty and "Family" in family_df.columns:
        ranked = family_df.sort_values("Conviction Rank") if "Conviction Rank" in family_df.columns else family_df
        for fam in ranked.head(10)["Family"].astype(str):
            family_digits.update(family4(fam))

    selected = []
    detail_rows = []
    ranked_by_pos = []
    labels = ["Ribu", "Ratus", "Puluh", "Unit"]
    for pos in range(4):
        max_base = max(score[pos].values()) if score[pos] else 1
        max_bridge = max(bridge_pos[pos].values()) if bridge_pos[pos] else 1
        ranked_digits = []
        for digit in "0123456789":
            base_pct = score[pos].get(digit, 0) / max_base * 100
            bridge_pct = bridge_pos[pos].get(digit, 0) / max_bridge * 15 if bridge_pos[pos] else 0
            family_bonus = min(family_digits.get(digit, 0), 5) * 1.5
            total = round(base_pct + bridge_pct + family_bonus, 2)
            ranked_digits.append((total, score[pos].get(digit, 0), digit, bridge_pct, family_bonus))
        ranked_digits.sort(key=lambda x: (-x[0], -x[1], x[2]))
        ranked_by_pos.append(ranked_digits)
        top = ranked_digits[:4]
        selected.append([x[2] for x in top])
        for rank, (total, raw_score, digit, bridge_score, family_bonus) in enumerate(top, 1):
            detail_rows.append({
                "Posisi": labels[pos], "Rank": rank, "Digit": digit,
                "V3 Score": total, "Recent Weighted": round(raw_score, 2),
                "Latest Count": latest_count[pos].get(digit, 0),
                "Bridge Confirm": round(bridge_score, 2), "Family Confirm": round(family_bonus, 2),
            })

    # V3.1 candidate-board optimisation. Setiap posisi boleh kekal Top 4 atau
    # mengganti satu slot dengan digit Rank 5-7. Tiada digit dipaksa secara manual.
    target_rank = {}
    if family_df is not None and not family_df.empty and "Family" in family_df.columns:
        ranked_family = family_df.sort_values("Conviction Rank") if "Conviction Rank" in family_df.columns else family_df
        for idx, fam in enumerate(ranked_family.head(10)["Family"].astype(str).tolist(), 1):
            target_rank[family4(fam)] = idx
    column_options = []
    for pos in range(4):
        top7 = ranked_by_pos[pos][:7]
        # Fast V3.1.1: Top 3 dikunci; slot keempat menguji Rank 4-7 sahaja.
        # 4 pilihan setiap posisi = 256 board, berbanding 28,561 sebelum ini.
        options = []
        for fourth in top7[3:7]:
            option = list(top7[:3]) + [fourth]
            option.sort(key=lambda x: (-x[0], -x[1], x[2]))
            digits = tuple(x[2] for x in option)
            if digits not in options:
                options.append(digits)
        column_options.append(options)

    digit_score = [{x[2]: x[0] for x in ranked_by_pos[pos]} for pos in range(4)]
    tetris_placements = _tetris_placements_v31()
    best_board = selected
    best_key = None
    for cols in product(*column_options):
        candidate = [list(col) for col in cols]
        matched = set()
        for _, cells in tetris_placements:
            fam = family4("".join(candidate[c][r] for r, c in cells))
            if fam in target_rank:
                matched.add(fam)
        bridge_value = sum(30 if target_rank[f] <= 3 else (20 if target_rank[f] <= 5 else 10) for f in matched)
        position_value = sum(digit_score[pos].get(d, 0) for pos in range(4) for d in candidate[pos])
        key = (round(position_value + bridge_value, 4), len(matched), round(position_value, 4))
        if best_key is None or key > best_key:
            best_key = key; best_board = candidate
    selected = best_board

    # Rebuild detail mengikut board yang benar-benar dipilih V3.1.
    detail_rows = []
    for pos in range(4):
        lookup = {x[2]: x for x in ranked_by_pos[pos]}
        for rank, digit in enumerate(selected[pos], 1):
            total, raw_score, _, bridge_score, family_bonus = lookup[digit]
            detail_rows.append({
                "Posisi": labels[pos], "Rank": rank, "Digit": digit, "V3.1 Score": total,
                "Recent Weighted": round(raw_score, 2), "Latest Count": latest_count[pos].get(digit, 0),
                "Bridge Confirm": round(bridge_score, 2), "Family Confirm": round(family_bonus, 2),
            })

    exact_df, near_df = _tetris_matches_v31(selected, target_rank)
    chart_text = "\n".join("   ".join(selected[pos][rank] for pos in range(4)) for rank in range(4))
    latest = recent.iloc[-1]
    meta = {
        "DrawNo": str(latest.get("DrawNo", "")), "DrawDate": str(latest.get("DrawDate", "")),
        "Lookback": len(recent), "Combinations": 4 ** 4, "Selected": selected,
        "Exact Matches": exact_df, "Near Matches": near_df,
    }
    return chart_text, pd.DataFrame(detail_rows), meta


@st.cache_data(show_spinner=False)
def load_full_result_data_v3():
    fp = Path("TotoFullResult.xlsx")
    return pd.read_excel(fp) if fp.exists() else pd.DataFrame()




try:
    # Show chart only after Generate produced Pair Arrangement.
    if "pair_arr_df" in locals():
        chart_text, chart_detail_df, chart_meta = build_result_chart_board_v3(
            load_full_result_data_v3(),
            bridge_df=bridge_df if "bridge_df" in locals() else pd.DataFrame(),
            family_df=bridge_family_rank_df if "bridge_family_rank_df" in locals() else pd.DataFrame(),
            lookback=12,
        )
        if chart_text:
            st.subheader("📊 Result Chart Board V3.1")
            st.caption(
                f"Data-driven | Full Result hingga Draw {chart_meta.get('DrawNo', '')} | "
                f"Lookback {chart_meta.get('Lookback', 0)} draw | 4×4 = {chart_meta.get('Combinations', 256)} kemungkinan"
            )
            copy_button_clean(
                "📋 Copy Chart Board V3.1",
                "📊 Rumah A Predictor - Result Chart Board V3.1\n\n" + chart_text,
                "result_chart_board_v3_1"
            )
            st.code(chart_text, language=None)
            st.caption("Board ini ialah 256 kombinasi posisi, bukan 16 nombor shortlist.")
            exact_matches = chart_meta.get("Exact Matches", pd.DataFrame())
            near_matches = chart_meta.get("Near Matches", pd.DataFrame())
            if exact_matches is not None and not exact_matches.empty:
                st.markdown("**Exact Bridge Tetris:** " + " / ".join(exact_matches["Family"].drop_duplicates().tolist()))
                with st.expander("Lihat bentuk Exact Tetris", expanded=False):
                    st.dataframe(exact_matches, hide_index=True, use_container_width=True)
            else:
                st.info("Tiada Exact Bridge Tetris pada board ini.")
            if near_matches is not None and not near_matches.empty:
                with st.expander("Lihat 3D near-match (bukan exact)", expanded=False):
                    st.dataframe(near_matches.head(30), hide_index=True, use_container_width=True)
            with st.expander("Lihat sebab digit V3.1 dipilih", expanded=False):
                st.dataframe(chart_detail_df, hide_index=True, use_container_width=True)
            st.caption("📝 Pastikan Full Results terbaru dikemaskini untuk analisis draw seterusnya.")
except Exception:
    pass
