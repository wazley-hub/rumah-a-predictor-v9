"""
ranking_engine.py
=================
Enjin ranking dinamik untuk Rumah A Predictor (tanpa import streamlit).

Masalah asal
------------
1. Ranking pair Bridge disusun ikut "Total Support" KEDUDUKAN (1st Front,
   1st Middle ... 3rd Back) dalam 100 draw terakhir, kemudian tie-break ikut
   urutan tetap (1st Front dahulu). Sokongan kedudukan hampir tidak berubah
   dari draw ke draw, jadi pair dalam kedudukan yang sama asyik naik atas.
2. Route Signal membandingkan hit rate mentah dua laluan yang jumlah calonnya
   berbeza (contoh 41 vs 66). Laluan yang calonnya lebih banyak sentiasa
   nampak lebih baik kerana liputan, bukan kerana lebih tepat.

Penyelesaian
------------
* Setiap pair dinilai dengan  SKOR = peluang_rawak_semasa x lift
    - peluang_rawak_semasa : liputan box sebenar pair ITU pada draw semasa
      (berubah ikut digit existing/missing draw terkini)
    - lift : (hit / jangkaan) berpemberat susut-masa (half-life), gabungan
      bukti kedudukan dan bukti pair itu sendiri, dengan shrinkage ke 1.0
* Route Signal dibanding menggunakan lift (hit / jangkaan liputan).
* Shortlist Top-N konsensus untuk mengurangkan bilangan nombor.

Nota jujur: lift hanya mengukur apa yang berlaku dalam sejarah. Gunakan
`pair_ranking_diagnostics` untuk menguji sama ada susunan ini benar-benar
meramal draw seterusnya melebihi peluang rawak.
"""

from __future__ import annotations

import math
from collections import Counter
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

SPACE = 10_000
PRIZES = 3
SLOTS = [
    ("1st", "Front", 0, "first"), ("1st", "Middle", 1, "first"), ("1st", "Back", 2, "first"),
    ("2nd", "Front", 0, "second"), ("2nd", "Middle", 1, "second"), ("2nd", "Back", 2, "second"),
    ("3rd", "Front", 0, "third"), ("3rd", "Middle", 1, "third"), ("3rd", "Back", 2, "third"),
]
DIGITS = "0123456789"


# --------------------------------------------------------------------------
# Asas
# --------------------------------------------------------------------------
def pad4(value) -> str:
    return str(value).strip().split(".")[0].zfill(4)[-4:]


def key4(number: str) -> str:
    return "".join(sorted(pad4(number)))


_BOX_SIZE_CACHE: Dict[str, int] = {}


def box_size_of_key(key: str) -> int:
    if key not in _BOX_SIZE_CACHE:
        size = math.factorial(len(key))
        for c in Counter(key).values():
            size //= math.factorial(c)
        _BOX_SIZE_CACHE[key] = size
    return _BOX_SIZE_CACHE[key]


def coverage_of_keys(keys: Iterable[str]) -> float:
    return min(1.0, sum(box_size_of_key(k) for k in set(keys)) / SPACE)


def route_chance(keys: Iterable[str]) -> float:
    """Peluang rawak sekurang-kurangnya satu daripada 3 hadiah masuk set box ini."""
    return 1.0 - (1.0 - coverage_of_keys(keys)) ** PRIZES


def route_lift(matches: Sequence[dict], hit_field: str, exp_field: str, prior: float = 2.0) -> float:
    """
    Lift laluan dalam kumpulan keadaan: (jumlah hit + prior) / (jumlah jangkaan + prior).
    Prior menarik lift ke 1.0 bila sampel kecil. Membandingkan lift (bukan hit
    rate mentah) membuang kelebihan palsu laluan yang calonnya lebih banyak.
    """
    hits = sum(1.0 for m in matches if m[hit_field])
    exp = sum(float(m[exp_field]) for m in matches)
    return (hits + prior) / (exp + prior)


def _slot_keys(pair: str, existing: List[str], missing: List[str]):
    v1 = {key4(f"{pair}{m}{e}") for m in missing for e in existing}
    v2 = {
        key4(f"{pair}{a}{b}")
        for pool in (missing, existing)
        for a in pool for b in pool if a != b
    }
    return v1, v2


def _digits_of(numbers: Sequence[str]):
    existing = sorted(set("".join(numbers)))
    missing = sorted(set(DIGITS) - set(existing))
    return existing, missing


# --------------------------------------------------------------------------
# Jadual transisi pair (dikira sekali, digunakan semula)
# --------------------------------------------------------------------------
def build_pair_table(history: pd.DataFrame, first_index: int = 0) -> pd.DataFrame:
    """
    Satu baris bagi setiap (draw sumber s, kedudukan). hit = v1/v2 hit pada
    draw s+1. Baris draw terakhir tiada hit (NaN) tetapi exp/cov tetap ada.
    """
    h = history.reset_index(drop=True)
    firsts = [pad4(v) for v in h["first"]]
    seconds = [pad4(v) for v in h["second"]]
    thirds = [pad4(v) for v in h["third"]]
    n = len(h)
    rows = []
    for s in range(max(0, first_index), n):
        nums = {"first": firsts[s], "second": seconds[s], "third": thirds[s]}
        existing, missing = _digits_of(list(nums.values()))
        targets = None
        if s + 1 < n:
            targets = {key4(firsts[s + 1]), key4(seconds[s + 1]), key4(thirds[s + 1])}
        for slot_id, (src, pos, start, col) in enumerate(SLOTS):
            pair = nums[col][start:start + 2]
            v1, v2 = _slot_keys(pair, existing, missing)
            union = v1 | v2
            cov = coverage_of_keys(union)
            rows.append({
                "src": s, "slot": slot_id, "Source": src, "Pair Position": pos,
                "pair": pair, "pairkey": "".join(sorted(pair)),
                "v1_hit": np.nan if targets is None else float(bool(v1 & targets)),
                "v2_hit": np.nan if targets is None else float(bool(v2 & targets)),
                "hit": np.nan if targets is None else float(bool(union & targets)),
                "cov": cov, "exp": 1.0 - (1.0 - cov) ** PRIZES,
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Ranking dinamik
# --------------------------------------------------------------------------
def _decayed_lift(hit: np.ndarray, exp: np.ndarray, age: np.ndarray,
                  half_life: float, prior: float) -> float:
    if hit.size == 0:
        return 1.0
    w = np.power(0.5, age / max(half_life, 1.0))
    return float((np.sum(w * hit) + prior) / (np.sum(w * exp) + prior))


def rank_pairs_from_table(
    table: pd.DataFrame,
    now_src: int,
    window: int = 500,
    half_life: float = 80.0,
    lookback_raw: int = 100,
) -> pd.DataFrame:
    """
    Ranking pair untuk draw sumber `now_src` menggunakan HANYA transisi yang
    sudah lengkap sebelum itu (src < now_src).
    """
    cur = table[table["src"] == now_src].sort_values("slot")
    ev = table[(table["src"] < now_src) & (table["src"] >= now_src - window) & table["hit"].notna()]
    ev_age = (now_src - 1 - ev["src"].to_numpy()).astype(float)

    rows = []
    for _, c in cur.iterrows():
        m_slot = (ev["slot"] == c["slot"]).to_numpy()
        m_pair = (ev["pairkey"] == c["pairkey"]).to_numpy()
        lift_slot = _decayed_lift(ev["hit"].to_numpy()[m_slot], ev["exp"].to_numpy()[m_slot],
                                  ev_age[m_slot], half_life, prior=6.0)
        lift_pair = _decayed_lift(ev["hit"].to_numpy()[m_pair], ev["exp"].to_numpy()[m_pair],
                                  ev_age[m_pair], half_life, prior=6.0)
        lift = 0.5 * lift_slot + 0.5 * lift_pair
        recent = ev[(ev["src"] >= now_src - lookback_raw) & (ev["slot"] == c["slot"])]
        trans = int(ev[(ev["src"] >= now_src - lookback_raw)]["src"].nunique())
        rows.append({
            "Source": c["Source"], "Pair Position": c["Pair Position"],
            "Current Pair": c["pair"],
            "V1 Hit": int(recent["v1_hit"].sum()), "V2 Hit": int(recent["v2_hit"].sum()),
            "Total Support": int(recent["hit"].sum()),
            "Hit Rate %": round(float(recent["hit"].mean()) * 100, 1) if len(recent) else 0.0,
            "Transitions": trans,
            "Liputan %": round(float(c["cov"]) * 100, 2),
            "Rawak %": round(float(c["exp"]) * 100, 2),
            "Lift": round(lift, 3),
            "Skor %": round(min(1.0, float(c["exp"]) * lift) * 100, 2),
            "_pairkey": c["pairkey"], "_slot": int(c["slot"]),
        })
    ranked = pd.DataFrame(rows).sort_values(
        ["Skor %", "Liputan %", "Current Pair"], ascending=[False, False, True], kind="stable"
    )
    ranked = ranked.drop_duplicates("_pairkey", keep="first").reset_index(drop=True)
    ranked.insert(0, "Priority", range(1, len(ranked) + 1))
    return ranked


def build_bridge_pair_priority_dynamic(
    history: pd.DataFrame, first, second, third,
    lookback: int = 100, evidence_window: int = 500, half_life: float = 80.0,
) -> pd.DataFrame:
    """
    Pengganti `build_bridge_pair_priority`. Lajur lama dikekalkan, lajur baru
    (Liputan %, Rawak %, Lift, Skor %) ditambah. Disusun daripada skor tertinggi.
    """
    columns = ["Priority", "Source", "Pair Position", "Current Pair", "V1 Hit", "V2 Hit",
               "Total Support", "Hit Rate %", "Transitions"]
    if history is None or len(history) < 2:
        return pd.DataFrame(columns=columns)
    h = history.reset_index(drop=True)
    start = max(0, len(h) - int(max(evidence_window, lookback)) - 1)
    table = build_pair_table(h.iloc[start:].reset_index(drop=True))

    # Draw semasa mengikut parameter (biasanya baris terakhir history).
    nums = {"first": pad4(first), "second": pad4(second), "third": pad4(third)}
    existing, missing = _digits_of(list(nums.values()))
    now_src = int(table["src"].max()) + 1
    cur_rows = []
    for slot_id, (src, pos, st, col) in enumerate(SLOTS):
        pair = nums[col][st:st + 2]
        v1, v2 = _slot_keys(pair, existing, missing)
        cov = coverage_of_keys(v1 | v2)
        cur_rows.append({"src": now_src, "slot": slot_id, "Source": src, "Pair Position": pos,
                         "pair": pair, "pairkey": "".join(sorted(pair)),
                         "v1_hit": np.nan, "v2_hit": np.nan, "hit": np.nan,
                         "cov": cov, "exp": 1.0 - (1.0 - cov) ** PRIZES})
    # Buang baris draw terakhir dalam jadual (belum ada hasil) dan ganti dengan draw semasa.
    table = table[table["src"] < int(table["src"].max())]
    table = pd.concat([table, pd.DataFrame(cur_rows)], ignore_index=True)
    ranked = rank_pairs_from_table(table, now_src, window=evidence_window,
                                   half_life=half_life, lookback_raw=lookback)
    return ranked.drop(columns=["_pairkey", "_slot"])


# --------------------------------------------------------------------------
# Diagnostik: adakah susunan berubah, dan adakah ia meramal?
# --------------------------------------------------------------------------
def _binom_sf(hits: int, n: int, p: float) -> float:
    if n <= 0:
        return float("nan")
    if hits <= 0:
        return 1.0
    p = min(max(p, 1e-12), 1 - 1e-12)
    lp, lq = math.log(p), math.log1p(-p)
    tot = 0.0
    for i in range(hits, n + 1):
        t = math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
        tot += t
        if i > hits + 60 and t < 1e-16:
            break
    return min(1.0, tot)


def pair_ranking_diagnostics(
    history: pd.DataFrame, test_draws: int = 500,
    evidence_window: int = 500, half_life: float = 80.0,
) -> Dict[str, pd.DataFrame]:
    """
    Walk-forward: untuk setiap draw ujian, susun pair menggunakan data sebelumnya,
    kemudian semak sama ada pair ranking teratas (dan setiap ranking) hit pada draw seterusnya.
    Juga bandingkan kepelbagaian dengan kaedah lama (kedudukan tetap).
    """
    h = history.reset_index(drop=True)
    n = len(h)
    test_draws = min(test_draws, n - 2)
    first_src = n - 1 - test_draws
    table = build_pair_table(h, first_index=max(0, first_src - evidence_window - 1))

    new_top, old_top = [], []
    rank_hits: Dict[int, List[float]] = {}
    rank_exp: Dict[int, List[float]] = {}
    for s in range(first_src, n - 1):
        rk = rank_pairs_from_table(table, s, window=evidence_window, half_life=half_life)
        nxt = table[(table["src"] == s)][["slot", "hit", "pairkey"]]
        hit_by_key = {r["pairkey"]: r["hit"] for _, r in nxt.iterrows()}
        new_top.append(f'{rk.loc[0, "Source"]} {rk.loc[0, "Pair Position"]}')
        for i, r in rk.iterrows():
            rank_hits.setdefault(i + 1, []).append(hit_by_key[r["_pairkey"]])
            rank_exp.setdefault(i + 1, []).append(r["Rawak %"] / 100.0)
        # Kaedah lama: Total Support (100 draw) kemudian V1 kemudian urutan tetap
        win = table[(table["src"] < s) & (table["src"] >= s - 100) & table["hit"].notna()]
        sup = win.groupby("slot")[["hit", "v1_hit"]].sum()
        sup = sup.reindex(range(9)).fillna(0)
        order = sorted(range(9), key=lambda sl: (-sup.loc[sl, "hit"], -sup.loc[sl, "v1_hit"], sl))
        sl0 = order[0]
        old_top.append(f"{SLOTS[sl0][0]} {SLOTS[sl0][1]}")

    def change_rate(seq):
        return float(np.mean([a != b for a, b in zip(seq[:-1], seq[1:])])) if len(seq) > 1 else 0.0

    diversity = pd.DataFrame([
        {"Kaedah": "Lama (kedudukan tetap)", "Slot teratas berbeza": len(set(old_top)),
         "Kadar berubah antara draw %": round(change_rate(old_top) * 100, 1),
         "Slot paling kerap di atas %": round(Counter(old_top).most_common(1)[0][1] / len(old_top) * 100, 1)},
        {"Kaedah": "Baru (skor dinamik)", "Slot teratas berbeza": len(set(new_top)),
         "Kadar berubah antara draw %": round(change_rate(new_top) * 100, 1),
         "Slot paling kerap di atas %": round(Counter(new_top).most_common(1)[0][1] / len(new_top) * 100, 1)},
    ])

    rows = []
    for rank in sorted(rank_hits):
        hits = np.array(rank_hits[rank], dtype=float)
        exp = np.array(rank_exp[rank], dtype=float)
        k, m, pe = int(hits.sum()), len(hits), float(exp.mean())
        rows.append({"Ranking": rank, "Draw": m, "Hit": k, "Hit %": round(k / m * 100, 2),
                     "Jangkaan rawak %": round(pe * 100, 2), "p-value": round(_binom_sf(k, m, pe), 4)})
    by_rank = pd.DataFrame(rows)
    if not by_rank.empty:
        by_rank["p terlaras"] = (by_rank["p-value"] * len(by_rank)).clip(upper=1.0).round(4)
    return {"diversity": diversity, "by_rank": by_rank,
            "top_slot_counts": pd.Series(Counter(new_top)).sort_values(ascending=False).rename("Kali di ranking 1").to_frame()}


# --------------------------------------------------------------------------
# Shortlist Top-N konsensus (kurangkan bilangan nombor)
# --------------------------------------------------------------------------
def rank_candidates_consensus(
    frames: Dict[str, pd.DataFrame],
    support: Optional[Dict[str, float]] = None,
    top_n: int = 10,
    number_col: str = "No Terhasil",
) -> pd.DataFrame:
    """
    Gabung calon daripada beberapa route/engine, satu baris bagi setiap keluarga
    box. Skor = jumlah (1 + sokongan route) bagi route yang menjana keluarga itu,
    ditambah bonus log2 bagi bilangan laluan formula berbeza yang menjana nombor
    itu dalam route yang sama. Kemudian ambil `top_n` teratas.

    `support[name]` = bilangan undi keadaan Route Signal (0..4), supaya route yang
    disokong oleh keadaan draw semasa diberi pemberat lebih. Heuristik konsensus:
    tidak disahkan secara statistik.
    """
    support = support or {}
    fam: Dict[str, dict] = {}
    for name, frame in frames.items():
        if frame is None or frame.empty or number_col not in frame.columns:
            continue
        counts = Counter(pad4(v) for v in frame[number_col].dropna().astype(str))
        per_family: Dict[str, Counter] = {}
        for number, c in counts.items():
            per_family.setdefault(key4(number), Counter())[number] += c
        for key, cnt in per_family.items():
            total_paths = sum(cnt.values())
            rec = fam.setdefault(key, {"routes": [], "score": 0.0, "numbers": Counter()})
            rec["routes"].append(name)
            rec["score"] += (1.0 + float(support.get(name, 0))) * (1.0 + math.log2(total_paths))
            rec["numbers"].update(cnt)
    rows = []
    for key, rec in fam.items():
        best_number = rec["numbers"].most_common(1)[0][0]
        rows.append({"Calon": best_number, "Keluarga": key, "Route": " + ".join(rec["routes"]),
                     "Bil Route": len(rec["routes"]), "Skor": round(rec["score"], 2),
                     "Liputan box": box_size_of_key(key)})
    out = pd.DataFrame(rows, columns=["Calon", "Keluarga", "Route", "Bil Route", "Skor", "Liputan box"])
    if out.empty:
        return out
    out = out.sort_values(["Skor", "Bil Route", "Calon"], ascending=[False, False, True]).reset_index(drop=True)
    out.insert(0, "Rank", range(1, len(out) + 1))
    return out.head(int(top_n)).reset_index(drop=True)


# --------------------------------------------------------------------------
# Susunan nombor dalam satu pair (V1 / V2)
# --------------------------------------------------------------------------
def rank_pair_numbers(
    number_df: pd.DataFrame,
    history: Optional[pd.DataFrame] = None,
    top_n: Optional[int] = None,
    window: int = 500,
    half_life: float = 150.0,
) -> pd.DataFrame:
    """
    Susun nombor hasil Bridge V1/V2 bagi satu pair daripada paling berpeluang.

    1. Peluang box = bilangan susunan digit berbeza (1..24). Nombor 4 digit
       berbeza ada 24 susunan; 1122 hanya 6. Ini peluang sebenar jika padanan box.
    2. Kekerapan terkini keluarga box itu dalam `window` draw (susut-masa), supaya
       susunan berubah mengikut draw terkini.
    3. Bila skor sama, nombor yang dijana oleh lebih banyak route diutamakan,
       kemudian nombor itu sendiri (deterministik).
    """
    if number_df is None or number_df.empty:
        return number_df
    df = number_df.copy()
    df["_key"] = df["No"].astype(str).map(key4)
    df["_box"] = df["_key"].map(box_size_of_key)
    recent = Counter()
    if history is not None and len(history) > 0:
        h = history.reset_index(drop=True).tail(int(window))
        n = len(h)
        for age, (_, row) in enumerate(reversed(list(h.iterrows()))):
            w = 0.5 ** (age / max(half_life, 1.0))
            for col in ("first", "second", "third"):
                recent[key4(row[col])] += w
    df["_recent"] = df["_key"].map(lambda k: recent.get(k, 0.0))
    df["_routes"] = df.groupby("_key")["Route"].transform("nunique")
    df["Peluang Box %"] = (df["_box"] / SPACE * 100).round(3)
    df["Skor Terkini"] = df["_recent"].round(3)
    df = df.sort_values(["_box", "_recent", "_routes", "No"],
                        ascending=[False, False, False, True], kind="stable")
    if top_n:
        df = df.head(int(top_n))
    return df.drop(columns=["_key", "_box", "_recent", "_routes"]).reset_index(drop=True)
