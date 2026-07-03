from pathlib import Path

# === Result Chart Board ===
def load_full_result_chart():
    """
    Read TotoFullResult.xlsx.
    Priority:
    1. Local file in Streamlit app root.
    2. GitHub file named TotoFullResult.xlsx in same repo/branch.

    Supports wide format:
    DrawNo, DrawDate, 1stPrizeNo, 2ndPrizeNo, 3rdPrizeNo,
    SpecialNo1..10, ConsolationNo1..10.
    """
    try:
        from io import BytesIO
        import base64
        import requests

        df = None

        # 1) Local first
        try:
            if Path("TotoFullResult.xlsx").exists():
                df = pd.read_excel("TotoFullResult.xlsx")
        except Exception:
            df = None

        # 2) GitHub fallback
        if df is None or df.empty:
            try:
                token = get_github_token()
                headers = github_headers()
                url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/TotoFullResult.xlsx"
                r = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=30)
                if r.status_code == 200:
                    content = r.json().get("content", "")
                    if content:
                        raw = base64.b64decode(content)
                        df = pd.read_excel(BytesIO(raw))
            except Exception:
                pass

        if df is None or df.empty:
            return "", "Carta belum tersedia."

        if "DrawNo" in df.columns:
            df["_draw_sort"] = pd.to_numeric(df["DrawNo"], errors="coerce")
            latest = df.sort_values("_draw_sort").iloc[-1]
            draw_no = str(int(float(latest.get("DrawNo", 0)))).zfill(6)
        else:
            latest = df.iloc[-1]
            draw_no = ""

        number_cols = [c for c in df.columns if c not in ["DrawNo", "DrawDate", "_draw_sort"]]

        nums = []
        for c in number_cols:
            n = _chart_pad4(latest.get(c, ""))
            if n:
                nums.append(n)

        if not nums:
            return "", "Carta belum tersedia."

        digits = "".join(nums)
        counts = {str(i): digits.count(str(i)) for i in range(10)}
        ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))

        top_digits = [d for d, _ in ordered[:5]]
        rows = []
        for i in range(5):
            rows.append(" ".join(top_digits[(i + j) % len(top_digits)] for j in range(4)))

        return "\n".join(rows), draw_no

    except Exception:
        return "", "Carta belum tersedia."


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


    # -----------------------------
    # Result Chart Board
    # -----------------------------
    st.subheader("📊 Result Chart Board")

    try:
        chart_text, chart_draw_no = load_full_result_chart()

        if chart_text:
            chart_copy_text = "📊 Rumah A Predictor - Result Chart Board\n\n"
            if chart_draw_no:
                chart_copy_text += f"Draw: {chart_draw_no}\n\n"
            chart_copy_text += chart_text

            copy_button_clean(
                "📋 Copy Chart Board",
                chart_copy_text,
                "result_chart_board"
            )

            st.code(chart_text, language=None)
        else:
            st.code("Carta belum tersedia.", language=None)

        st.caption("📝 Sila upload Full Results terbaru ke GitHub untuk paparan carta draw seterusnya.")

    except Exception:
        st.code("Carta belum tersedia.", language=None)
        st.caption("📝 Sila upload Full Results terbaru ke GitHub untuk paparan carta draw seterusnya.")


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


