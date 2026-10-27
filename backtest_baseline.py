"""
backtest_baseline.py
====================
Modul backtest jujur untuk Rumah A Predictor.

Tujuan: setiap model dibandingkan dengan PELUANG RAWAK (chance baseline), bukan
hanya dilaporkan "hit rate" kosong. Dua cara padanan diasingkan:

  * EXACT : nombor tepat sama (contoh 7103 == 7103)
  * BOX   : digit disusun semula dikira sama (contoh 3170 == 7103)

Padanan box meliputi sehingga 24 nombor bagi setiap calon, jadi hit rate
boleh nampak tinggi (50%+) walaupun ia sama sahaja dengan kebetulan. Modul
ini menghitung "jangkaan kalau rawak" berdasarkan liputan sebenar setiap
senarai calon, kemudian beri p-value (binomial, satu hala).

Modul ini TIDAK import streamlit, jadi boleh diuji dan dijalankan sendiri:

    python backtest_baseline.py TotoHistoryAll.xlsx --draws 2000 --k 10

Penting: p-value kecil untuk satu strategi di antara banyak yang diuji masih
boleh berlaku kerana kebetulan. Jadual menyediakan p-value terlaras
(Bonferroni) - gunakan lajur itu untuk membuat kesimpulan.
"""

from __future__ import annotations

import argparse
import itertools
import math
import random
from collections import Counter, deque
from typing import Callable, Dict, Iterable, List, Sequence

import pandas as pd

SPACE = 10_000  # semua nombor 0000-9999
PRIZES_PER_DRAW = 3  # 1st, 2nd, 3rd


# --------------------------------------------------------------------------
# Utiliti asas
# --------------------------------------------------------------------------
def pad4(value) -> str:
    return str(value).strip().split(".")[0].zfill(4)[-4:]


def box_key(number: str) -> str:
    return "".join(sorted(pad4(number)))


def box_size(number: str) -> int:
    """Bilangan nombor berbeza yang sama box dengan `number` (1..24)."""
    counts = Counter(pad4(number))
    size = math.factorial(4)
    for c in counts.values():
        size //= math.factorial(c)
    return size


def prepare_draws(history: pd.DataFrame) -> List[List[str]]:
    """
    Tukar DataFrame sejarah kepada senarai [first, second, third] mengikut
    susunan kronologi. Terima nama kolum app (first/second/third) atau fail
    asal (1stPrizeNo/2ndPrizeNo/3rdPrizeNo).
    """
    df = history.copy()
    rename = {"1stPrizeNo": "first", "2ndPrizeNo": "second", "3rdPrizeNo": "third",
              "DrawDate": "draw_date", "DrawNo": "draw_no"}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ("first", "second", "third"):
        if col not in df.columns:
            raise ValueError(f"Kolum '{col}' tiada dalam sejarah.")
    df = df.dropna(subset=["first", "second", "third"])
    if "draw_date" in df.columns:
        df["_d"] = pd.to_numeric(df["draw_date"], errors="coerce")
        df = df.sort_values("_d", kind="stable")
    return [[pad4(r[0]), pad4(r[1]), pad4(r[2])]
            for r in df[["first", "second", "third"]].values]


def chance_exact(k: int) -> float:
    """Kebarangkalian sekurang-kurangnya satu daripada k nombor (berbeza) tepat
    sama dengan salah satu daripada 3 hadiah (hypergeometrik)."""
    k = max(0, min(k, SPACE))
    return 1.0 - math.comb(SPACE - k, PRIZES_PER_DRAW) / math.comb(SPACE, PRIZES_PER_DRAW)


def coverage_box(numbers: Iterable[str]) -> float:
    """Nisbah ruang 0000-9999 yang dilindungi (padanan box) oleh senarai ini."""
    seen = {}
    for n in numbers:
        seen[box_key(n)] = box_size(n)
    return min(1.0, sum(seen.values()) / SPACE)


def chance_box(numbers: Iterable[str]) -> float:
    cov = coverage_box(numbers)
    return 1.0 - (1.0 - cov) ** PRIZES_PER_DRAW


def binom_sf(hits: int, n: int, p: float) -> float:
    """P(X >= hits), X ~ Binomial(n, p). Tepat, tanpa scipy."""
    if n <= 0:
        return float("nan")
    if hits <= 0:
        return 1.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    log_p, log_q = math.log(p), math.log1p(-p)
    total = 0.0
    for i in range(hits, n + 1):
        log_term = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                    + i * log_p + (n - i) * log_q)
        total += math.exp(log_term)
        if i > hits + 50 and math.exp(log_term) < 1e-18 * max(total, 1e-300):
            break
    return min(1.0, total)


# --------------------------------------------------------------------------
# Penilai generik: boleh dipakai untuk enjin APA-APA (termasuk Bridge V1/V2)
# --------------------------------------------------------------------------
def evaluate_candidate_lists(
    candidate_lists: Sequence[Sequence[str]],
    results: Sequence[Sequence[str]],
    label: str = "model",
) -> dict:
    """
    candidate_lists[i] = calon yang dijana SEBELUM draw i
    results[i]         = [first, second, third] sebenar draw i
    Mengembalikan hit exact & box berbanding jangkaan rawak + p-value.
    """
    n = len(results)
    if n != len(candidate_lists):
        raise ValueError("Bilangan senarai calon mesti sama dengan bilangan keputusan.")
    ex_hits = bx_hits = 0
    ex_exp = bx_exp = 0.0
    cov_sum = 0.0
    used = 0
    for cands, res in zip(candidate_lists, results):
        cands = [pad4(c) for c in cands]
        if not cands:
            continue
        used += 1
        res = [pad4(r) for r in res]
        cset = set(cands)
        bset = {box_key(c) for c in cands}
        ex_hits += any(r in cset for r in res)
        bx_hits += any(box_key(r) in bset for r in res)
        ex_exp += chance_exact(len(cset))
        bx_exp += chance_box(cands)
        cov_sum += coverage_box(cands)
    if used == 0:
        return {"Model": label, "Draw diuji": 0}
    p_ex, p_bx = ex_exp / used, bx_exp / used
    return {
        "Model": label,
        "Draw diuji": used,
        "Purata calon": round(sum(len(set(c)) for c in candidate_lists if c) / used, 1),
        "Liputan box %": round(cov_sum / used * 100, 2),
        "Exact hit": ex_hits,
        "Exact %": round(ex_hits / used * 100, 2),
        "Exact rawak %": round(p_ex * 100, 2),
        "Exact p-value": binom_sf(ex_hits, used, p_ex),
        "Box hit": bx_hits,
        "Box %": round(bx_hits / used * 100, 2),
        "Box rawak %": round(p_bx * 100, 2),
        "Box p-value": binom_sf(bx_hits, used, p_bx),
    }


def bridge_vs_chance(detail_df: pd.DataFrame, result_col: str = "Next Result") -> pd.DataFrame:
    """
    Bandingkan Bridge V1 / V2 (daripada jadual Detail backtest sedia ada)
    dengan peluang rawak. Hanya draw yang sudah selesai (ada keputusan) dikira.
    """
    specs = [("Bridge V1", "Bridge List"), ("Bridge V2", "Bridge V2 List")]
    rows = []
    done = detail_df[detail_df[result_col].astype(str).str.contains("/", na=False)]
    done = done[done["Bridge Hit"].isin(["YES", "NO"])] if "Bridge Hit" in done else done
    results = [[x.strip() for x in str(r).split("/")][:3] for r in done[result_col]]
    for label, col in specs:
        if col not in done.columns:
            continue
        lists = [[x.strip() for x in str(v).split("/") if x.strip().isdigit()]
                 for v in done[col]]
        rows.append(evaluate_candidate_lists(lists, results, label))
    out = pd.DataFrame(rows)
    return add_adjusted_p(out)


def add_adjusted_p(table: pd.DataFrame) -> pd.DataFrame:
    """Tambah p-value terlaras Bonferroni (didarab bilangan model diuji)."""
    if table.empty:
        return table
    m = len(table)
    for col in ("Exact p-value", "Box p-value"):
        if col in table:
            table[col.replace("p-value", "p terlaras")] = (table[col] * m).clip(upper=1.0)
    return table


# --------------------------------------------------------------------------
# Strategi top-K (walk-forward, hanya guna data SEBELUM draw)
# --------------------------------------------------------------------------
def _top_k_counter(counter: Counter, k: int) -> List[str]:
    return [n for n, _ in counter.most_common(k)]


def make_strategies(window: int = 300) -> Dict[str, Callable]:
    """
    Setiap strategi ialah kelas stateful dengan .pick(k) dan .update(draw).
    Dijana semula pada setiap larian supaya tiada kebocoran data.
    """

    class FreqAll:
        name = "Paling kerap (semua sejarah)"

        def __init__(self):
            self.c = Counter()

        def update(self, draw):
            self.c.update(draw)

        def pick(self, k):
            return _top_k_counter(self.c, k)

    class FreqRecent:
        name = f"Paling kerap ({window} draw terkini)"

        def __init__(self):
            self.c, self.q = Counter(), deque()

        def update(self, draw):
            self.q.append(draw)
            self.c.update(draw)
            if len(self.q) > window:
                for n in self.q.popleft():
                    self.c[n] -= 1
                    if self.c[n] <= 0:
                        del self.c[n]

        def pick(self, k):
            return _top_k_counter(self.c, k)

    class Overdue:
        name = "Paling lama tak keluar (overdue)"

        def __init__(self):
            self.last, self.i = {}, 0

        def update(self, draw):
            for n in draw:
                self.last[n] = self.i
            self.i += 1

        def pick(self, k):
            return sorted(self.last, key=self.last.get)[:k]

    class DigitPos:
        name = "Skor digit ikut kedudukan"

        def __init__(self):
            self.pos, self.q = [Counter() for _ in range(4)], deque()

        def _apply(self, draw, sign):
            for n in draw:
                for p, ch in enumerate(n):
                    self.pos[p][ch] += sign

        def update(self, draw):
            self.q.append(draw)
            self._apply(draw, +1)
            if len(self.q) > window:
                self._apply(self.q.popleft(), -1)

        def pick(self, k):
            tops = [[d for d, _ in self.pos[p].most_common(4)] for p in range(4)]
            scored = sorted(
                ((sum(self.pos[p][ch] for p, ch in enumerate(t)), "".join(t))
                 for t in itertools.product(*tops)),
                reverse=True,
            )
            return [s for _, s in scored[:k]]

    class Rand:
        name = "Rawak (kawalan)"

        def __init__(self):
            self.rng = random.Random(20260101)

        def update(self, draw):
            pass

        def pick(self, k):
            return [f"{self.rng.randrange(SPACE):04d}" for _ in range(k)]

    return {s.name: s for s in (FreqAll, FreqRecent, Overdue, DigitPos, Rand)}


def run_walk_forward(
    draws: Sequence[Sequence[str]],
    test_draws: int = 2000,
    k: int = 10,
    window: int = 300,
) -> pd.DataFrame:
    """
    Untuk setiap draw dalam `test_draws` terakhir: strategi hanya nampak draw
    sebelumnya, pilih k nombor, kemudian semak terhadap draw itu.
    """
    n = len(draws)
    test_draws = min(test_draws, n - 1)
    start = n - test_draws
    strategies = {name: cls() for name, cls in make_strategies(window).items()}
    for d in draws[:start]:
        for s in strategies.values():
            s.update(list(d))
    picks: Dict[str, List[List[str]]] = {name: [] for name in strategies}
    for i in range(start, n):
        for name, s in strategies.items():
            picks[name].append(s.pick(k))
        for s in strategies.values():
            s.update(list(draws[i]))
    results = [list(d) for d in draws[start:]]
    rows = [evaluate_candidate_lists(picks[name], results, name) for name in strategies]
    return add_adjusted_p(pd.DataFrame(rows))


# --------------------------------------------------------------------------
# Ringkasan kesimpulan (teks) untuk paparan di app
# --------------------------------------------------------------------------
def verdict(table: pd.DataFrame, alpha: float = 0.05) -> str:
    if table.empty:
        return "Tiada data untuk dinilai."
    col = "Exact p terlaras" if "Exact p terlaras" in table else "Exact p-value"
    rand_free = table[~table["Model"].str.contains("Rawak", na=False)]
    good = rand_free[rand_free[col] < alpha]
    if good.empty:
        return ("Tiada model yang mengalahkan peluang rawak secara signifikan "
                f"(p terlaras >= {alpha}). Hit rate yang kelihatan tinggi adalah "
                "dijangka daripada liputan calon sahaja.")
    names = ", ".join(good["Model"])
    return (f"Model berikut melepasi ujian (p terlaras < {alpha}): {names}. "
            "Sahkan pada tempoh data lain (out-of-sample) sebelum mempercayainya.")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Backtest top-K vs peluang rawak")
    ap.add_argument("xlsx", help="TotoHistoryAll.xlsx")
    ap.add_argument("--draws", type=int, default=2000, help="bilangan draw diuji")
    ap.add_argument("--k", type=int, default=10, help="bilangan nombor dipilih")
    ap.add_argument("--window", type=int, default=300)
    ap.add_argument("--out", default="backtest_vs_random.xlsx")
    args = ap.parse_args()

    draws = prepare_draws(pd.read_excel(args.xlsx))
    table = run_walk_forward(draws, args.draws, args.k, args.window)
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print(table.to_string(index=False))
    print("\n" + verdict(table))
    table.to_excel(args.out, index=False)
    print(f"\nDisimpan: {args.out}")


if __name__ == "__main__":
    main()
