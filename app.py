
import streamlit as st
import pandas as pd
import requests
import base64
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from io import BytesIO

st.set_page_config(page_title="Rumah A Predictor V11", layout="wide")
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

    return {
        "hybrid": make_table(hybrid, 20),
        "stat": make_table(stat_cand, 10),
        "position": make_table(pos_cand, 10),
        "pair": make_table(pair_cand, 10),
        "theory": make_table(theory_cand, 20),
        "audit": audit_summary,
    }

def reset_audit_cache():
    build_audit.clear()

def reset_all_caches():
    build_audit.clear()
    load_base_history.clear()

if "history" not in st.session_state:
    st.session_state.history = load_base_history().copy()

st.title("Rumah A Predictor V11")
st.caption("V11: tambah keputusan baru dan auto-save terus ke GitHub jika token sudah diset.")

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

with st.expander("Tambah keputusan baru ke history app", expanded=True):
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
        auto_save = st.checkbox("Auto-save ke GitHub", value=True)
        add_clicked = st.form_submit_button("Simpan keputusan")

    if add_clicked:
        if not (new_first and new_second and new_third):
            st.error("Sila isi 1st, 2nd dan 3rd.")
        else:
            new_row = {
                "draw_no": next_draw,
                "draw_date": draw_date,
                "first": pad4(new_first),
                "second": pad4(new_second),
                "third": pad4(new_third),
            }
            new_history = pd.concat([st.session_state.history, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.history = new_history
            reset_audit_cache()
            if auto_save:
                ok, msg = update_github_excel(new_history)
                if ok:
                    st.success("Keputusan baru disimpan dan GitHub berjaya dikemaskini.")
                    reset_all_caches()
                else:
                    st.warning("Keputusan baru disimpan dalam sesi app, tetapi GitHub belum dikemaskini.")
                    st.error(msg)
            else:
                st.success("Keputusan baru disimpan dalam sesi app sahaja.")
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
    st.success("Ramalan berjaya dijana.")

    st.subheader("Top 20 Hybrid")
    st.dataframe(result["hybrid"], hide_index=True, use_container_width=True)

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

st.caption("Jika auto-save GitHub aktif, fail TotoHistoryAll.xlsx dalam repo akan dikemaskini automatik.")
st.caption("Ini alat eksperimen statistik sahaja, bukan jaminan keputusan.")
