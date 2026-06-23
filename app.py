
import streamlit as st
import pandas as pd
import requests
import base64
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from io import BytesIO

st.set_page_config(page_title="Rumah A Predictor V17.1 Fix", layout="wide")
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
        df[c] = df[c].astype(str)
    for c in ["first", "second", "third"]:
        df[c] = df[c].apply(pad4)
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
            "Model": ["Statistik", "Peralihan Posisi", "Pasangan", "Teori Pasangan"],
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
        "Teori Pasangan": {"hits": 0, "tests": 0},
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
            "Teori Pasangan": res["theory"],
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
        "Model": ["Statistik", "Peralihan Posisi", "Pasangan", "Teori Pasangan"],
        "Accuracy %": [0, 0, 0, 0],
        "Suggested Weight %": [25, 25, 25, 25],
        "Basis": ["Default"] * 4,
    })

def champion_number_engine(result, cold_rebound_df, hot_reversal_df, top_n=20):
    """
    V17.1 Fix:
    Weighted champion score:
    70% normalized hybrid + 20% cold rebound + 10% hot trend.
    Ini beri ruang ranking berubah tanpa membunuh model asal.
    """
    cold_scores = dict(zip(cold_rebound_df["Digit"], cold_rebound_df["Cold Rebound Score"])) if cold_rebound_df is not None else {}
    hot_signals = dict(zip(hot_reversal_df["Digit"], hot_reversal_df["Signal"])) if hot_reversal_df is not None else {}

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

        champion_score = (hybrid_norm * 0.70) + (cold_norm * 0.20) + (hot_norm * 0.10)

        rows.append({
            "No": no,
            "Hybrid Norm": round(hybrid_norm, 2),
            "Cold Norm": round(cold_norm, 2),
            "Hot Norm": round(hot_norm, 2),
            "Champion Score": round(champion_score, 3),
        })

    df = pd.DataFrame(rows).sort_values("Champion Score", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df.head(top_n)

def make_prediction_report_excel(result, hot_df, cold_df, inputs):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        pd.DataFrame([inputs]).to_excel(writer, sheet_name="Input", index=False)
        result["hybrid_all"].to_excel(writer, sheet_name="Top Hybrid", index=False)
        if "breakdown" in result:
            result["breakdown"].to_excel(writer, sheet_name="Score Breakdown", index=False)
        if "accuracy_tracker" in result:
            result["accuracy_tracker"].to_excel(writer, sheet_name="Model Accuracy", index=False)
        if "adaptive_weights" in result:
            result["adaptive_weights"].to_excel(writer, sheet_name="Adaptive Weights", index=False)
        if "cold_rebound" in result:
            result["cold_rebound"].to_excel(writer, sheet_name="Cold Rebound", index=False)
        if "hot_reversal" in result:
            result["hot_reversal"].to_excel(writer, sheet_name="Hot Reversal", index=False)
        if "champion" in result:
            result["champion"].to_excel(writer, sheet_name="Champion Engine", index=False)
        result["stat"].to_excel(writer, sheet_name="Model Statistik", index=False)
        result["position"].to_excel(writer, sheet_name="Model Peralihan", index=False)
        result["pair"].to_excel(writer, sheet_name="Model Pasangan", index=False)
        result["theory"].to_excel(writer, sheet_name="Teori Pasangan", index=False)
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

if "history" not in st.session_state:
    st.session_state.history = load_base_history().copy()

if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []

st.title("Rumah A Predictor V17.1 Fix")
st.caption("V17.1 Fix: Score Breakdown lebih jelas, Accuracy Tracker lebih ketat, dan Champion Engine weighted.")

history = st.session_state.history
last = history.iloc[-1]

st.subheader("Keputusan terakhir dalam data app")
st.write({
    "Draw No": str(last["draw_no"]),
    "Draw Date": str(last["draw_date"]),
    "1st": last["first"],
    "2nd": last["second"],
    "3rd": last["third"],
    "Jumlah Draw": len(history),
})

token_status = "Aktif" if get_github_token() else "Belum diset"
st.info(f"Status GitHub auto-save: {token_status}")


# -----------------------------
# V14: History Manager Lengkap
# -----------------------------
st.subheader("Dataset Statistics")
stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
stat_c1.metric("Jumlah Draw", len(st.session_state.history))
stat_c2.metric("Draw Pertama", str(st.session_state.history.iloc[0]["draw_no"]))
stat_c3.metric("Draw Terakhir", str(st.session_state.history.iloc[-1]["draw_no"]))
stat_c4.metric("Tarikh Terakhir", str(st.session_state.history.iloc[-1]["draw_date"]))

st.subheader("History Manager")

search_draw = st.text_input("Cari Draw No", value="", placeholder="Contoh: 614826")
view_df = st.session_state.history.copy()

if search_draw.strip():
    view_df = view_df[view_df["draw_no"].astype(str).str.contains(search_draw.strip(), case=False, na=False)]
    st.caption(f"Keputusan carian untuk Draw No mengandungi: {search_draw.strip()}")
else:
    view_df = view_df.tail(10)
    st.caption("Paparan 10 draw terakhir")

recent_view = view_df.copy().rename(columns={
    "draw_no": "Draw No",
    "draw_date": "Draw Date",
    "first": "1st",
    "second": "2nd",
    "third": "3rd",
})
st.dataframe(recent_view.iloc[::-1], hide_index=True, use_container_width=True)

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
        st.download_button(
            "Download Latest GitHub History",
            data=latest_bytes,
            file_name="TotoHistoryAll_latest_github.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_github_history",
        )
    else:
        st.info("Latest GitHub History belum boleh dimuat turun. Pastikan token aktif.")

with st.expander("Edit / padam draw daripada history", expanded=False):
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

with st.expander("Tambah / update keputusan ke history app", expanded=True):
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
    st.subheader("Generate ramalan")
    c1, c2, c3 = st.columns(3)
    first = c1.text_input("1st Prize", value=last["first"], max_chars=4)
    second = c2.text_input("2nd Prize", value=last["second"], max_chars=4)
    third = c3.text_input("3rd Prize", value=last["third"], max_chars=4)
    submitted = st.form_submit_button("Generate")

if submitted:
    result = generate(st.session_state.history, first, second, third)
    cold_df_for_engine = cold_rebound_engine(st.session_state.history, window=cold_window if "cold_window" in globals() else 100)
    hot_reversal_for_engine = hot_reversal_detector(st.session_state.history, window=hot_window if "hot_window" in globals() else 30)
    accuracy_df = model_accuracy_tracker(st.session_state.history, lookback=100)

    result["breakdown"] = score_breakdown_table(
        result["hybrid_all"],
        result["stat"],
        result["position"],
        result["pair"],
        result["theory"],
    )
    result["accuracy_tracker"] = accuracy_df
    result["adaptive_weights"] = adaptive_weight_engine(result, accuracy_df)
    result["cold_rebound"] = cold_df_for_engine
    result["hot_reversal"] = hot_reversal_for_engine
    result["champion"] = champion_number_engine(result, cold_df_for_engine, hot_reversal_for_engine, top_n=20)
    st.success("Ramalan berjaya dijana.")

    top_n = st.selectbox("Pilih jumlah Top Hybrid", [20, 50, 100], index=0)
    hybrid_view = result["hybrid_all"].head(top_n).copy()

    st.subheader(f"Top {top_n} Hybrid + Confidence")
    st.dataframe(hybrid_view, hide_index=True, use_container_width=True)

    st.subheader("Score Breakdown - Top Hybrid")
    st.dataframe(result["breakdown"].head(top_n), hide_index=True, use_container_width=True)

    st.subheader("Model Accuracy Tracker")
    st.dataframe(result["accuracy_tracker"], hide_index=True, use_container_width=True)

    st.subheader("Adaptive Weight Engine")
    st.dataframe(result["adaptive_weights"], hide_index=True, use_container_width=True)

    st.subheader("Cold Rebound Engine")
    st.dataframe(result["cold_rebound"], hide_index=True, use_container_width=True)

    st.subheader("Hot Reversal Detector")
    st.dataframe(result["hot_reversal"], hide_index=True, use_container_width=True)

    st.subheader("Champion Number Engine")
    st.dataframe(result["champion"], hide_index=True, use_container_width=True)

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

    report_file = make_prediction_report_excel(result, hot_df, cold_df, report_inputs)
    st.download_button(
        "Download Prediction Report Excel",
        data=report_file,
        file_name=f"Prediction_Report_{report_inputs['Latest Draw No']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if len(result["hybrid_all"]) > 0:
        top_pick = result["hybrid_all"].iloc[0]
        pred_record = {
            "Latest Draw No": report_inputs["Latest Draw No"],
            "Input 1st": pad4(first),
            "Input 2nd": pad4(second),
            "Input 3rd": pad4(third),
            "Top Pick": top_pick["No"],
            "Top Score": top_pick["Score"],
            "Top Confidence": top_pick["Confidence"],
        }
        if pred_record not in st.session_state.prediction_history:
            st.session_state.prediction_history.append(pred_record)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Model Statistik")
        st.dataframe(result["stat"], hide_index=True, use_container_width=True)
    with c2:
        st.subheader("Model Peralihan Posisi")
        st.dataframe(result["position"], hide_index=True, use_container_width=True)
    with c3:
        st.subheader("Model Pasangan")
        st.dataframe(result["pair"], hide_index=True, use_container_width=True)

    st.subheader("Teori Pasangan")
    st.dataframe(result["theory"], hide_index=True, use_container_width=True)

    st.subheader("Hot / Cold Digit Analysis")
    hc1, hc2 = st.columns(2)
    with hc1:
        st.write("Hot Digits")
        st.dataframe(hot_df, hide_index=True, use_container_width=True)
    with hc2:
        st.write("Cold Digits")
        st.dataframe(cold_df, hide_index=True, use_container_width=True)

    st.subheader("Prediction History")
    if st.button("Clear Prediction History"):
        st.session_state.prediction_history = []
        st.rerun()
    pred_hist_df = pd.DataFrame(st.session_state.prediction_history)
    st.dataframe(pred_hist_df, hide_index=True, use_container_width=True)
    if not pred_hist_df.empty:
        st.download_button(
            "Download Prediction History CSV",
            data=pred_hist_df.to_csv(index=False).encode("utf-8"),
            file_name="prediction_history.csv",
            mime="text/csv",
        )

    st.subheader("Audit Ringkas")
    audit = result["audit"]
    st.write("Missing digits:", " ".join(audit["missing"]) if audit["missing"] else "-")
    st.write("Top recent digits:", " ".join(audit["top_recent"]))
    st.write("Top missing-next:", " ".join(audit["top_missing_next"]))
    st.write("Top pairs:")
    st.dataframe(pd.DataFrame(audit["top_pairs"], columns=["Pair", "Warisan %"]), hide_index=True)
    st.write("Position choices:")
    st.dataframe(pd.DataFrame({
        "Pos 1": audit["pos_choice"][0],
        "Pos 2": audit["pos_choice"][1],
        "Pos 3": audit["pos_choice"][2],
        "Pos 4": audit["pos_choice"][3],
    }), hide_index=True)

st.caption("Ini alat eksperimen statistik sahaja, bukan jaminan keputusan.")

