
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

def score_add(d, num, score):
    if len(num) == 4 and max_repeat(num) <= 2:
        d[num] += score

def add_perm4(d, a, b, c, e, score):
    combos = [
        (a,b,c,e,1.00), (a,b,e,c,0.96), (a,c,b,e,0.93),
        (a,c,e,b,0.90), (b,a,c,e,0.88), (c,a,b,e,0.86),
        (e,c,b,a,0.82),
    ]
    for x1,x2,x3,x4,m in combos:
        score_add(d, x1+x2+x3+x4, score*m)

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
    s = 0
    for pos, d in enumerate(num):
        s += audit_data["pos_trans"][(pos, cur_first[pos])][d] / 45
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


def generate(history, first, second, third):
    nums = [pad4(first), pad4(second), pad4(third)]
    audit_data = build_audit(history)
    present = set("".join(nums))
    missing = [d for d in "0123456789" if d not in present]
    input_pairs = list(dict.fromkeys(get_pairs(nums)))
    current_pair_score = {p: audit_data["pair_rate"].get(p, 0) for p in input_pairs}
    top_pairs = top_keys(current_pair_score, 9)
    top_recent = top_keys(audit_data["recent100"], 10)
    top_missing_next = top_keys(audit_data["missing_next"], 10)

    cur_first = nums[0]
    pos_choice = []
    for pos in range(4):
        pos_choice.append(top_keys(audit_data["pos_trans"][(pos, cur_first[pos])], 4))

    stat_cand, pos_cand, pair_cand, theory_cand, hybrid = (
        defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    )

    m1 = missing[0] if len(missing) >= 1 else top_recent[0]
    m2 = missing[1] if len(missing) >= 2 else top_recent[1]

    if top_pairs:
        tp = top_pairs[0]
        for rd in top_recent[:4]:
            for mn in top_missing_next[:3]:
                add_perm4(stat_cand, m1, rd, tp[0], mn, 15)
                add_perm4(stat_cand, m1, m2, rd, mn, 14)
                add_perm4(stat_cand, m1, rd, tp[1], m2, 13)

    for x1, x2, x3, x4 in product(range(4), repeat=4):
        num = pos_choice[0][x1] + pos_choice[1][x2] + pos_choice[2][x3] + pos_choice[3][x4]
        sc = 20 - ((x1+1)+(x2+1)+(x3+1)+(x4+1))
        score_add(pos_cand, num, sc + num_position_score(num, audit_data, cur_first))

    present_list = list(present)
    for rank, pr in enumerate(top_pairs[:9], start=1):
        for md in missing:
            for pdig in present_list:
                add_perm4(theory_cand, pr[0], pr[1], md, pdig, 12 + (10-rank))
                score_add(pair_cand, pr + md + pdig, 15 + (10-rank))
                score_add(pair_cand, pr + pdig + md, 13 + (10-rank))
            for rd in top_recent[:4]:
                score_add(pair_cand, pr + md + rd, 12 + (10-rank))
                score_add(pair_cand, pr + rd + md, 11 + (10-rank))

    for source in [stat_cand, pos_cand, pair_cand, theory_cand]:
        for num, base_score in source.items():
            sc = base_score
            sc += num_stat_score(num, audit_data, set(missing), present)
            sc += num_position_score(num, audit_data, cur_first)
            sc += num_pair_score(num, audit_data, current_pair_score)
            score_add(hybrid, num, sc)

    audit_summary = {
        "missing": missing,
        "top_pairs": [(p, round(current_pair_score[p]*100, 2)) for p in top_pairs],
        "top_recent": top_recent[:10],
        "top_missing_next": top_missing_next[:10],
        "pos_choice": pos_choice,
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

with st.form("predict_form"):
    st.subheader("🎲 Generate Ramalan")
    st.caption("Keputusan terbaru telah diisi secara automatik. Tekan Generate untuk dapatkan AI Pick dan pilihan nombor.")
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
    st.success("Ramalan berjaya dijana.")

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
    st.subheader("🧠 Core Prediction Models")
    st.caption("Empat model utama dipaparkan dahulu supaya mudah audit dan copy ke WhatsApp.")

    with st.expander("📊 Model Statistik", expanded=False):
        st.dataframe(result["stat"], hide_index=True, use_container_width=True)

    with st.expander("🔁 Model Peralihan Posisi", expanded=False):
        st.dataframe(result["position"], hide_index=True, use_container_width=True)

    with st.expander("🔗 Model Pasangan", expanded=False):
        st.dataframe(result["pair"], hide_index=True, use_container_width=True)

    with st.expander("🔢 Model No Double", expanded=False):
        st.dataframe(result["theory"], hide_index=True, use_container_width=True)

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

    st.subheader("📋 Copy Ramalan Model")
    st.caption("Copy semua senarai model untuk paste ke WhatsApp.")

    copy_button_clean("📋 Copy Semua Ramalan Model", model_share_text, "all_models_fixed")

    st.text_area(
        "Ramalan Model untuk WhatsApp",
        value=model_share_text,
        height=220,
        label_visibility="collapsed"
    )


    st.subheader("🎯 AI Decision Engine")

    top3_df = decision_simple.iloc[0:3].copy()
    top3_list = top3_df["No"].tolist()
    top3_text = " / ".join(top3_list)

    strong_extra = decision_simple.iloc[3:10].copy()
    backup_pool = decision_simple.iloc[10:15].copy()

    strong_extra_list = strong_extra["No"].tolist()
    backup_list = backup_pool["No"].tolist()
    strong_text = " / ".join(strong_extra_list)
    backup_text = " / ".join(backup_list)

    st.markdown(
        f"""
        <div style="border:1px solid #e6e6e6;border-radius:14px;padding:14px 16px;margin-bottom:14px;background:#ffffff;">
            <div style="font-size:17px;line-height:1.9;">
                <b>🔥 AI Pick</b> &nbsp;&nbsp;: <span style="font-size:26px;font-weight:900;letter-spacing:2px;">{ai_pick_no}</span>
                <span style="font-size:16px;"> {ai_pick_rating} ({ai_pick_conf})</span><br>
                <b>🥇 Top 3</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {top3_text}<br>
                <b>⭐ Strong Buy</b> : {strong_text}<br>
                <b>🎯 Backup</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {backup_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("📋 Quick Share WhatsApp")
    st.caption("Satu kotak bersih untuk copy dan paste ke WhatsApp.")

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



    copy_button_clean("📋 Copy Semua", share_text, "all")

    st.success(
        "Cadangan ringkas: salin Top 3 untuk pilihan utama, atau Copy Semua untuk kongsi penuh di WhatsApp."
    )

    # -----------------------------
    # V26.5: Signal variables only
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
    # V27.2: Signal Strength Score
    # -----------------------------
    st.subheader("⭐ Signal Strength Score")
    st.caption("Skor gabungan ringkas berdasarkan model utama + pattern signal. Tidak mengubah AI Pick atau ranking asal.")

    try:
        score_model_sources = [
            ("Statistik", signal_stat_nums),
            ("Peralihan", signal_position_nums),
            ("Pasangan", signal_pair_nums),
            ("No Double", signal_nodouble_nums),
        ]

        signal_score_df = build_signal_strength_score(
            score_model_sources,
            family_df=globals().get("family_df", None),
            pair_signal_df=pair_signal_df,
            dd_df=globals().get("dd_df", None),
            triple_df=globals().get("triple_df", None),
        )

        if signal_score_df.empty:
            st.info("Belum ada Signal Strength Score untuk dipaparkan.")
        else:
            signal_score_share = f"""⭐ Rumah A Predictor - Signal Strength Score

Top Score:
{' / '.join(signal_score_df.head(10)['No'].astype(str).tolist())}

Detail:
{chr(10).join([f"{row['No']} - {row['Score']} ({row['Source']} | {row['Pattern']})" for _, row in signal_score_df.head(10).iterrows()])}
"""
            copy_button_clean("📋 Copy Signal Score", signal_score_share, "signal_score")

            with st.expander("Lihat Jadual Signal Strength Score", expanded=False):
                st.dataframe(signal_score_df.head(20), hide_index=True, use_container_width=True)

    except Exception:
        st.warning("Signal Strength Score belum dapat dipaparkan untuk ramalan ini.")


    # -----------------------------
    # V28: Selection Engine
    # -----------------------------
    st.subheader("🏆 Selection Engine")
    st.caption("Lapisan pemilihan tambahan berdasarkan weight audit/backtest awal. Tidak mengubah AI Pick asal.")

    try:
        selection_sources = [
            ("Statistik", signal_stat_nums),
            ("Peralihan", signal_position_nums),
            ("Pasangan", signal_pair_nums),
            ("No Double", signal_nodouble_nums),
        ]

        selection_df = build_selection_engine_v28(
            selection_sources,
            family_df=globals().get("family_df", None),
            pair_signal_df=pair_signal_df,
            dd_df=globals().get("dd_df", None),
            triple_df=globals().get("triple_df", None),
        )

        if selection_df.empty:
            st.info("Selection Engine belum ada calon untuk dipaparkan.")
        else:
            selection_top = selection_df.head(5)["No"].astype(str).tolist()
            selection_watch = selection_df.iloc[5:15]["No"].astype(str).tolist()

            selection_share_text = f"""🏆 Rumah A Predictor - Selection Engine

🔥 High Priority:
{' / '.join(selection_top)}

⭐ Watchlist:
{' / '.join(selection_watch)}

Detail:
{chr(10).join([f"{row['No']} - {row['Selection Score']} ({row['Status']} | {row['Model Source']} | {row['Pattern Support']})" for _, row in selection_df.head(10).iterrows()])}
"""
            copy_button_clean("📋 Copy Selection Engine", selection_share_text, "selection_engine")

            with st.expander("Lihat Detail Selection Engine", expanded=False):
                st.dataframe(selection_df.head(20), hide_index=True, use_container_width=True)
                st.text_area(
                    "Selection Engine untuk WhatsApp",
                    value=selection_share_text,
                    height=230,
                    label_visibility="collapsed"
                )

    except Exception:
        st.warning("Selection Engine belum dapat dipaparkan untuk ramalan ini.")


    # -----------------------------
    # V29: Arrangement Engine
    # -----------------------------
    st.subheader("🧩 Arrangement Engine")
    st.caption("Menyusun susunan terbaik daripada family nombor. Tidak mengubah Selection Engine atau AI Pick.")

    try:
        if "selection_df" in locals() and selection_df is not None and not selection_df.empty:
            high_priority_arr = selection_df.head(5)["No"].astype(str).tolist()

            arrangement_share_parts = ["🧩 Rumah A Predictor - Arrangement Engine", ""]
            arrangement_tables = []

            for base_no in high_priority_arr:
                arr_df = build_arrangement_engine_v29(base_no, st.session_state.history, top_n=5)
                if not arr_df.empty:
                    top_arrs = arr_df["Arrangement"].astype(str).tolist()
                    arrangement_share_parts.append(f"{base_no}: {' / '.join(top_arrs)}")
                    arrangement_tables.append((base_no, arr_df))

            arrangement_share_text = "\n".join(arrangement_share_parts)
            copy_button_clean("📋 Copy Arrangement", arrangement_share_text, "arrangement_engine")

            with st.expander("Lihat Detail Arrangement Engine", expanded=False):
                st.markdown("#### Auto Arrangement - High Priority")
                for base_no, arr_df in arrangement_tables:
                    st.write(f"Family: {base_no}")
                    st.dataframe(arr_df, hide_index=True, use_container_width=True)
                st.text_area(
                    "Arrangement untuk WhatsApp",
                    value=arrangement_share_text,
                    height=220,
                    label_visibility="collapsed"
                )
        else:
            st.info("Arrangement Engine akan dipaparkan selepas Selection Engine dijana.")
    except Exception:
        st.warning("Arrangement Engine belum dapat dipaparkan untuk ramalan ini.")



    # -----------------------------
    # V30.8: Anchor Cluster Convergence
    # -----------------------------
    st.subheader("🧬 Anchor Cluster Convergence")
    st.caption("Eksperimen: Anchor 2D → Cluster → Hidden Family. Guna semua 50 nombor, tanpa scan history.")

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

        if acc_df.empty:
            st.info("Belum ada hidden family yang kuat.")
        else:
            copy_text = "🧬 Rumah A Predictor - Anchor Cluster Convergence\n\n"
            copy_text += "\n".join(acc_df["Family"].astype(str).tolist())

            copy_button_clean(
                "📋 Copy Anchor Cluster",
                copy_text,
                "anchor_cluster_convergence"
            )

            with st.expander("Lihat Detail Anchor Cluster Convergence", expanded=False):
                st.dataframe(acc_df, hide_index=True, use_container_width=True)
                st.text_area(
                    "Anchor Cluster untuk WhatsApp",
                    value=copy_text,
                    height=180,
                    label_visibility="collapsed"
                )

    except Exception:
        st.warning("Anchor Cluster Convergence belum dapat dipaparkan.")


    # -----------------------------
    # SAFE: Pair Assist All Anchor
    # -----------------------------
    st.subheader("🧩 Pair Assist All Anchor")
    st.caption("Ringkas: semua family Anchor Cluster digabungkan dengan semua pair result. Contoh 0148 + 02 → 0248.")

    try:
        if "acc_df" in locals() and acc_df is not None and not acc_df.empty and "Family" in acc_df.columns:
            _anchor_families_safe = acc_df["Family"].astype(str).tolist()
        else:
            _anchor_families_safe = []

        _result_pairs_safe = list(dict.fromkeys(get_pairs([pad4(first), pad4(second), pad4(third)])))

        pair_assist_safe_df, pair_assist_safe_lines = build_pair_assist_all_anchor_safe_v30(
            _anchor_families_safe,
            _result_pairs_safe
        )

        if pair_assist_safe_df.empty:
            st.info("Pair Assist belum ada family tambahan.")
        else:
            pair_assist_safe_text = "🧩 Rumah A Predictor - Pair Assist All Anchor\n\n"
            pair_assist_safe_text += "\n".join(pair_assist_safe_lines)

            copy_button_clean(
                "📋 Copy Pair Assist All Anchor",
                pair_assist_safe_text,
                "pair_assist_all_anchor_safe"
            )

            with st.expander("Lihat Detail Pair Assist All Anchor", expanded=False):
                st.write("Pair result:", " / ".join(_result_pairs_safe))
                st.dataframe(pair_assist_safe_df, hide_index=True, use_container_width=True)
                st.text_area(
                    "Pair Assist untuk WhatsApp",
                    value=pair_assist_safe_text,
                    height=260,
                    label_visibility="collapsed"
                )

    except Exception as e:
        st.warning(f"Pair Assist All Anchor belum dapat dipaparkan: {e}")



    # -----------------------------
    # Pair Assist Pick Engine
    # -----------------------------
    st.subheader("🎯 Pair Assist Pick Engine")
    st.caption("Memilih calon utama daripada Pair Assist All Anchor supaya senarai tidak terlalu banyak.")

    try:
        if "pair_assist_safe_df" in locals() and pair_assist_safe_df is not None and not pair_assist_safe_df.empty:
            _pair_df_for_pick = pair_assist_safe_df
        else:
            _pair_df_for_pick = pd.DataFrame()

        if "acc_df" in locals() and acc_df is not None and not acc_df.empty and "Family" in acc_df.columns:
            _anchor_for_pick = acc_df["Family"].astype(str).tolist()
        else:
            _anchor_for_pick = []

        _result_pairs_for_pick = list(dict.fromkeys(get_pairs([pad4(first), pad4(second), pad4(third)])))

        pair_pick_df = build_pair_assist_pick_engine_v30(
            _pair_df_for_pick,
            _result_pairs_for_pick,
            anchor_families=_anchor_for_pick,
            top_n=20,
        )

        if pair_pick_df.empty:
            st.info("Pair Assist Pick belum ada calon untuk dipaparkan.")
        else:
            high_priority = pair_pick_df.head(8)["No"].astype(str).tolist()
            watchlist = pair_pick_df.iloc[8:20]["No"].astype(str).tolist()

            pair_pick_text = f"""🎯 Rumah A Predictor - Pair Assist Pick Engine

🔥 High Priority:
{' / '.join(high_priority)}

👀 Watchlist:
{' / '.join(watchlist)}
"""

            copy_button_clean(
                "📋 Copy Pair Assist Pick",
                pair_pick_text,
                "pair_assist_pick_engine"
            )

            with st.expander("Lihat Detail Pair Assist Pick Engine", expanded=False):
                st.dataframe(pair_pick_df, hide_index=True, use_container_width=True)
                st.text_area(
                    "Pair Assist Pick untuk WhatsApp",
                    value=pair_pick_text,
                    height=180,
                    label_visibility="collapsed"
                )

    except Exception as e:
        st.warning(f"Pair Assist Pick belum dapat dipaparkan: {e}")



    # -----------------------------
    # Pair Assist Arrangement Engine
    # -----------------------------
    st.subheader("🎯 Pair Assist Arrangement Engine")
    st.caption("3 susunan terbaik bagi setiap family daripada Pair Assist Pick.")

    try:
        if "pair_pick_df" in locals() and pair_pick_df is not None and not pair_pick_df.empty:
            _pair_pick_df = pair_pick_df
        else:
            _pair_pick_df = pd.DataFrame()

        _result_pairs_arr = list(dict.fromkeys(get_pairs([pad4(first), pad4(second), pad4(third)])))

        pair_arr_df = build_pair_arrangement_engine_v30(
            _pair_pick_df,
            _result_pairs_arr,
            top_per_family=3,
        )

        if pair_arr_df.empty:
            st.info("Pair Arrangement belum ada data.")
        else:
            pair_arr_text = "🎯 Rumah A Predictor - Pair Assist Arrangement Engine\n\n"
            for _, r in pair_arr_df.iterrows():
                pair_arr_text += f"{r['Family']}: {r['Top Arrangement']}\n"

            copy_button_clean(
                "📋 Copy Pair Arrangement",
                pair_arr_text,
                "pair_arrangement_engine"
            )

            with st.expander("Lihat Detail Pair Arrangement", expanded=False):
                st.dataframe(pair_arr_df, hide_index=True, use_container_width=True)

    except Exception as e:
        st.warning(f"Pair Arrangement belum dapat dipaparkan: {e}")

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




# === Result Chart Board V2 4x4 FINAL ===
def load_full_result_chart_final():
    try:
        import pandas as pd
        from pathlib import Path
        from collections import Counter

        fp = Path("TotoFullResult.xlsx")
        if not fp.exists():
            return ""

        df = pd.read_excel(fp)
        if df.empty:
            return ""

        # latest draw only
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

            nums.append(s.zfill(4)[-4:])

        if not nums:
            return ""

        # V2 Position-Aware 4x4 BUGFIX
        # Satu carta sahaja:
        # Column 1 = ribu, Column 2 = ratus, Column 3 = puluh, Column 4 = unit.
        #
        # Formula sebenar:
        # Ambil Top 4 digit paling kerap bagi setiap posisi daripada latest full result.
        # Tiada priority hardcoded supaya board ikut data draw terkini sepenuhnya.
        cols = []
        for pos in range(4):
            pos_digits = [n[pos] for n in nums if len(n) == 4]
            counts = Counter(pos_digits)

            selected = [
                d for d, _ in sorted(
                    counts.items(),
                    key=lambda x: (-x[1], x[0])
                )[:4]
            ]

            # fallback sekiranya data pelik kurang daripada 4 digit unik
            if len(selected) < 4:
                for d in [str(i) for i in range(10)]:
                    if d not in selected:
                        selected.append(d)
                    if len(selected) == 4:
                        break

            cols.append(selected[:4])

        rows = []
        for r in range(4):
            rows.append("   ".join(cols[c][r] for c in range(4)))

        return "\n".join(rows)

    except Exception:
        return ""




try:
    # Show chart only after Generate produced Pair Arrangement.
    if "pair_arr_df" in locals():
        chart_text = load_full_result_chart_final()
        if chart_text:
            st.subheader("📊 Result Chart Board")
            copy_button_clean(
                "📋 Copy Chart Board",
                "📊 Rumah A Predictor - Result Chart Board\n\n" + chart_text,
                "result_chart_board"
            )
            st.code(chart_text, language=None)
            st.caption("📝 Sila upload Full Results terbaru ke GitHub untuk paparan carta draw seterusnya.")
except Exception:
    pass
