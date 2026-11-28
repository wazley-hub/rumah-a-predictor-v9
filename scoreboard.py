"""
scoreboard.py
=============
Papan prestasi: semak ramalan LALU terhadap keputusan sebenar dan bandingkan dengan
peluang rawak. Inilah cara satu-satunya untuk tahu sama ada sesuatu penambahbaikan itu
benar: setiap draw baharu menambah satu ujian yang tidak boleh dipilih selepas melihat
jawapan.

Cache (`scoreboard_cache.json`) menyimpan, bagi setiap draw sumber:
    {"top": [keluarga box Top-30 mengikut ranking], "bridge": [keluarga box Bridge V1+V2]}
Kunci ialah nombor draw sumber. Keputusan ramalan itu ialah draw SETERUSNYA dalam sejarah.

Modul ini tidak mengimport streamlit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd

from backtest_baseline import binom_sf
from ranking_engine import key4, route_chance

DEFAULT_NS = (10, 30)


def draw_id(value) -> str:
    """Seragamkan nombor draw: '621426', 621426.0 -> '621426'."""
    return str(int(float(str(value).strip())))


def load_cache(path) -> Dict[str, dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {str(k): v for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache: Dict[str, dict], path) -> bool:
    try:
        Path(path).write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
        return True
    except OSError:
        return False


def make_entry(ranked_keys: Iterable[str], bridge_keys: Iterable[str], top_n: int = 30) -> dict:
    return {"top": [str(k) for k in list(ranked_keys)[:top_n]], "bridge": sorted({str(k) for k in bridge_keys})}


def history_index(history: pd.DataFrame):
    """(senarai nombor draw mengikut tertib, peta nombor draw -> set keluarga box 3 hadiah)."""
    ids, prizes = [], {}
    for _, row in history.reset_index(drop=True).iterrows():
        d = draw_id(row["draw_no"])
        ids.append(d)
        prizes[d] = {key4(row["first"]), key4(row["second"]), key4(row["third"])}
    return ids, prizes


def completed_sources(history: pd.DataFrame, window: int) -> List[str]:
    """Draw sumber (yang ada draw seterusnya) dalam `window` draw terakhir yang lengkap."""
    ids, _ = history_index(history)
    return ids[:-1][-int(window):]


def verdict(hit: int, n: int, expected_hits: float, p_adj: float) -> str:
    if n < 30:
        return "Terlalu sedikit data"
    if p_adj < 0.05 and hit > expected_hits:
        return "Melebihi rawak (perlu disahkan pada draw baharu)"
    return "Setara rawak"


def evaluate(cache: Dict[str, dict], history: pd.DataFrame, window: int = 100,
             ns: Sequence[int] = DEFAULT_NS) -> dict:
    """
    Kira prestasi ramalan dalam `window` draw terakhir yang lengkap.
    Pulangan: {"rows": [...], "n_draws": int, "missing": [draw sumber tanpa cache], "window": int}.
    """
    ids, prizes = history_index(history)
    nxt = {ids[i]: ids[i + 1] for i in range(len(ids) - 1)}
    sources = completed_sources(history, window)
    missing = [s for s in sources if s not in cache]
    acc = {("top", n): [0, 0.0, 0] for n in ns}
    acc[("bridge", 0)] = [0, 0.0, 0]
    for s in sources:
        entry = cache.get(s)
        if not entry:
            continue
        actual = prizes[nxt[s]]
        for n in ns:
            keys = entry["top"][:n]
            if not keys:
                continue
            a = acc[("top", n)]
            a[2] += 1
            a[0] += bool(set(keys) & actual)
            a[1] += route_chance(keys)
        bridge = entry.get("bridge") or []
        if bridge:
            a = acc[("bridge", 0)]
            a[2] += 1
            a[0] += bool(set(bridge) & actual)
            a[1] += route_chance(bridge)
    labels = {("top", n): f"Top {n} route" for n in ns}
    labels[("bridge", 0)] = "Bridge V1 + V2 (senarai penuh)"
    rows = []
    for key, (hit, exp_sum, n) in acc.items():
        if n == 0:
            continue
        exp = exp_sum / n
        rows.append({"key": key, "label": labels[key], "n": n, "hit": hit, "hit_pct": hit / n * 100,
                     "exp_pct": exp * 100, "p": binom_sf(hit, n, exp)})
    m = max(len(rows), 1)
    for r in rows:
        r["p_adj"] = min(1.0, r["p"] * m)
        r["verdict"] = verdict(r["hit"], r["n"], r["exp_pct"] / 100 * r["n"], r["p_adj"])
    return {"rows": rows, "n_draws": len(sources) - len(missing), "missing": missing, "window": window}
