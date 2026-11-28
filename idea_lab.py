"""
idea_lab.py
===========
Makmal Idea: uji sebarang cara memilih nombor terhadap PELUANG RAWAK dengan kaedah yang
menghalang kita tertipu oleh kebetulan.

Tiga kawalan dibina terus ke dalam makmal:

1. Walk-forward  : setiap pilihan hanya menggunakan draw SEBELUM draw yang diuji.
2. Penemuan / pengesahan : tempoh ujian dibelah dua. Separuh lama ialah "penemuan" (boleh
   nampak bagus secara kebetulan); separuh baharu ialah "pengesahan" (ujian sebenar).
3. Pembetulan banyak ujian : setiap idea yang dicuba dalam satu sesi menambah bilangan ujian,
   dan nilai p pengesahan didarab dengan bilangan itu (Bonferroni). Semakin banyak idea
   dicuba, semakin tinggi bar untuk dianggap sebagai benar.

Menambah idea baharu: tulis satu kelas dengan kaedah `update(draw)` dan `pick(k)`
(lihat `FreqWindow` sebagai contoh) dan daftarkannya dalam `IDEAS`.

Modul ini tidak mengimport streamlit.
"""

from __future__ import annotations

import hashlib
import itertools
import random
from collections import Counter, OrderedDict, deque
from typing import Dict, List, Optional, Sequence

import pandas as pd

from backtest_baseline import evaluate_candidate_lists, pad4

SPACE = 10_000


# --------------------------------------------------------------------------
# Idea (strategi). Setiap strategi: update(draw: [3 nombor]) dan pick(k) -> [nombor]
# --------------------------------------------------------------------------
class FreqWindow:
    """Nombor yang paling kerap naik dalam `window` draw terakhir."""

    def __init__(self, window: int = 300):
        self.window, self.counts, self.queue = window, Counter(), deque()

    def update(self, draw):
        self.queue.append(list(draw))
        self.counts.update(draw)
        if len(self.queue) > self.window:
            for n in self.queue.popleft():
                self.counts[n] -= 1
                if self.counts[n] <= 0:
                    del self.counts[n]

    def pick(self, k):
        return [n for n, _ in sorted(self.counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


class Overdue:
    """Nombor yang paling lama tidak naik (semua sejarah)."""

    def __init__(self, window: int = 0):
        self.seen = OrderedDict()

    def update(self, draw):
        for n in draw:
            self.seen.pop(n, None)
            self.seen[n] = True

    def pick(self, k):
        return list(itertools.islice(self.seen.keys(), k))


class HotDigits:
    """Nombor yang dibina daripada digit paling kerap bagi setiap kedudukan dalam `window` draw."""

    def __init__(self, window: int = 300):
        self.window, self.pos, self.queue = window, [Counter() for _ in range(4)], deque()

    def _apply(self, draw, sign):
        for n in draw:
            for p, ch in enumerate(n):
                self.pos[p][ch] += sign

    def update(self, draw):
        self.queue.append(list(draw))
        self._apply(draw, +1)
        if len(self.queue) > self.window:
            self._apply(self.queue.popleft(), -1)

    def pick(self, k):
        tops = [[d for d, _ in self.pos[p].most_common(4)] for p in range(4)]
        scored = sorted(
            ((sum(self.pos[p][ch] for p, ch in enumerate(t)), "".join(t)) for t in itertools.product(*tops)),
            reverse=True,
        )
        return [s for _, s in scored[:k]]


class Neighbours:
    """Nombor yang berbeza satu digit daripada nombor draw terakhir (tertib mengikut cincang deterministik)."""

    def __init__(self, window: int = 0):
        self.last, self.t = [], 0

    def update(self, draw):
        self.last, self.t = list(draw), self.t + 1

    def pick(self, k):
        pool = set()
        for n in self.last:
            for p in range(4):
                for d in "0123456789":
                    if d != n[p]:
                        pool.add(n[:p] + d + n[p + 1:])
        pool -= set(self.last)
        order = sorted(pool, key=lambda x: hashlib.md5(f"{self.t}:{x}".encode()).hexdigest())
        return order[:k]


class RandomPick:
    """Kawalan: nombor rawak. Mesti sentiasa 'setara rawak'; jika tidak, ujian itu sendiri bermasalah."""

    def __init__(self, window: int = 0):
        self.rng = random.Random(20261101)

    def update(self, draw):
        pass

    def pick(self, k):
        return [f"{self.rng.randrange(SPACE):04d}" for _ in range(k)]


IDEAS: Dict[str, dict] = {
    "kerap": {"label": "Nombor paling kerap naik", "cls": FreqWindow, "uses_window": True},
    "jarang": {"label": "Nombor paling lama tak naik", "cls": Overdue, "uses_window": False},
    "digit": {"label": "Digit paling kerap setiap kedudukan", "cls": HotDigits, "uses_window": True},
    "terbitan": {"label": "Terbitan draw terakhir (tukar satu digit)", "cls": Neighbours, "uses_window": False},
    "rawak": {"label": "Kawalan: nombor rawak", "cls": RandomPick, "uses_window": False},
}


# --------------------------------------------------------------------------
# Data dan ujian
# --------------------------------------------------------------------------
def prizes_from_history(history: pd.DataFrame) -> List[List[str]]:
    """[[1st, 2nd, 3rd], ...] mengikut tertib. Terima lajur app (first/second/third) atau fail asal."""
    df = history.rename(columns={"1stPrizeNo": "first", "2ndPrizeNo": "second", "3rdPrizeNo": "third"})
    return [[pad4(a), pad4(b), pad4(c)] for a, b, c in df[["first", "second", "third"]].to_numpy()]


def run_idea(prizes: Sequence[Sequence[str]], idea: str, window: int = 300, n_picks: int = 10,
             test_draws: int = 1000, match: str = "box") -> dict:
    """
    Uji satu idea. `match` = "box" (digit boleh disusun semula) atau "exact" (nombor tepat).
    Tempoh ujian (`test_draws` draw terakhir) dibelah dua: penemuan dan pengesahan.
    """
    spec = IDEAS[idea]
    strat = spec["cls"](window) if spec["uses_window"] else spec["cls"]()
    n = len(prizes)
    test_draws = max(40, min(int(test_draws), n - 1))
    start = n - test_draws
    for d in prizes[:start]:
        strat.update(list(d))
    picks = []
    for i in range(start, n):
        picks.append(strat.pick(n_picks))      # hanya guna draw sebelum i
        strat.update(list(prizes[i]))
    results = [list(d) for d in prizes[start:]]
    mid = len(results) // 2
    halves = {
        "penemuan": evaluate_candidate_lists(picks[:mid], results[:mid], "penemuan"),
        "pengesahan": evaluate_candidate_lists(picks[mid:], results[mid:], "pengesahan"),
    }
    key_h, key_p = ("Box hit", "Box p-value") if match == "box" else ("Exact hit", "Exact p-value")
    key_pct, key_exp = ("Box %", "Box rawak %") if match == "box" else ("Exact %", "Exact rawak %")
    out = {"idea": idea, "label": spec["label"], "window": window if spec["uses_window"] else None,
           "n_picks": n_picks, "test_draws": test_draws, "match": match, "halves": {}}
    for name, r in halves.items():
        out["halves"][name] = {"n": r.get("Draw diuji", 0), "hit": r.get(key_h, 0), "hit_pct": r.get(key_pct, 0.0),
                               "exp_pct": r.get(key_exp, 0.0), "p": r.get(key_p, 1.0)}
    return out


def verdict(result: dict, k_tests: int) -> str:
    """Kesimpulan dalam Bahasa Melayu, dengan pembetulan bagi `k_tests` idea yang telah dicuba."""
    d, v = result["halves"]["penemuan"], result["halves"]["pengesahan"]
    if v["n"] < 100:
        return "Terlalu sedikit data untuk pengesahan"
    p_adj = min(1.0, v["p"] * max(k_tests, 1))
    if p_adj < 0.05 and v["hit_pct"] > v["exp_pct"] and d["hit_pct"] > d["exp_pct"]:
        return "Disahkan (perlu diulang pada draw baharu)"
    if d["p"] < 0.05 and d["hit_pct"] > d["exp_pct"]:
        return "Tidak disahkan: nampak baik pada penemuan tetapi tidak berulang pada pengesahan"
    return "Tiada kelebihan berbanding rawak"


class Tracker:
    """Rekod semua idea yang dicuba dalam satu sesi; bilangannya menentukan pembetulan Bonferroni."""

    def __init__(self, rows: Optional[List[dict]] = None):
        self.rows = rows if rows is not None else []

    def add(self, result: dict) -> dict:
        v = result["halves"]["pengesahan"]
        row = {"idea": result["label"], "tetingkap": result["window"], "bil nombor": result["n_picks"],
               "padanan": result["match"], "p pengesahan": v["p"]}
        self.rows.append(row)
        return row

    def table(self) -> pd.DataFrame:
        k = len(self.rows)
        df = pd.DataFrame(self.rows)
        if df.empty:
            return df
        df["p terlaras"] = (df["p pengesahan"] * k).clip(upper=1.0).round(3)
        df["p pengesahan"] = df["p pengesahan"].round(3)
        df.insert(0, "#", range(1, k + 1))
        return df
