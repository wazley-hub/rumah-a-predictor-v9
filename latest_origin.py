"""
latest_origin.py
================
Jelaskan "nombor yang baru naik datang daripada engine / laluan mana" terus
dalam app, tanpa perlu muat turun Excel backtest.

Input ialah jadual Detail daripada backtest sedia ada
(`run_backtest_bridge_dde_lite_v31_24_5`). Baris yang diperlukan ialah baris
yang `Next Draw` = draw terkini, iaitu ramalan yang dibuat daripada draw
sebelumnya, kemudian disemak dengan keputusan terkini.

Tiada import streamlit, jadi boleh diuji berasingan.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

# (label, [lajur nombor hit], [lajur laluan])  - sama dengan Quick Review dalam Excel
ENGINES: List[Tuple[str, List[str], List[str]]] = [
    ("Bridge V1", ["Bridge Hit Number", "Bridge Hit No"], []),
    ("Bridge V2", ["Bridge V2 Hit Number", "Bridge V2 Hit No"], []),
    ("Solo V1", ["Bridge Solo V1 Hit Number"], []),
    ("Solo V2", ["Bridge Solo V2 Hit Number"], []),
    ("1st 2D + Missing",
     ["1st2D+Missing2nd Bridge Hit Number", "1st2D+Missing3rd Bridge Hit Number"],
     ["1st2D+Missing2nd Hit Routes", "1st2D+Missing3rd Hit Routes"]),
    ("1st 2D + 2nd&3rd", ["1st2D+2nd3rd Bridge Hit Number"], ["1st2D+2nd3rd Hit Routes"]),
    ("2nd 2D + Missing", ["2D+Missing Hit Number"], ["2D+Missing Hit Routes"]),
    ("2nd 2D + 1st&3rd", ["2D+1st3rd Hit Number"], ["2D+1st3rd Hit Routes"]),
    ("3rd 2D + Missing", ["3rd2D+Missing Bridge Hit Number"], ["3rd2D+Missing Hit Routes"]),
    ("3rd 2D + 1st&2nd", ["3rd2D+1st2nd Bridge Hit Number"], ["3rd2D+1st2nd Hit Routes"]),
]


def _pad4(value) -> str:
    return str(value).strip().split(".")[0].zfill(4)[-4:]


def _key(value) -> str:
    return "".join(sorted(_pad4(value)))


def _split_numbers(cell) -> List[str]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    return [p.strip() for p in str(cell).split("/") if p.strip().isdigit()]


def _route_snippets(cell, prize_key: str) -> List[str]:
    """Ambil laluan yang menghasilkan nombor bagi hadiah ini daripada teks 'Hit Routes'."""
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    out = []
    for segment in str(cell).split("||"):
        match = re.search(r"->\s*(\d{4})\s*$", segment.strip())
        if not match or _key(match.group(1)) != prize_key:
            continue
        head = segment.split("|")[0].strip().replace(" x ", " × ")
        if head:
            out.append(f"Kedudukan {head}")
    return out


def find_latest_row(detail_df: pd.DataFrame, latest_draw_no) -> Optional[pd.Series]:
    """Baris yang `Next Draw` = draw terkini (ramalan sebelum draw ini)."""
    if detail_df is None or detail_df.empty or "Next Draw" not in detail_df.columns:
        return None
    wanted = str(latest_draw_no).strip()
    rows = detail_df[detail_df["Next Draw"].astype(str).str.strip() == wanted]
    if rows.empty:
        return None
    return rows.iloc[-1]


def explain_latest_numbers(
    detail_df: pd.DataFrame, latest_draw_no, latest_numbers: List[str]
) -> Optional[Dict]:
    """
    Kembalikan {"source_draw", "source_result", "table"} atau None.
    table: satu baris bagi 1st/2nd/3rd - nombor, engine yang menjana, laluan.
    """
    row = find_latest_row(detail_df, latest_draw_no)
    if row is None:
        return None
    records = []
    for prize, number in zip(("1st", "2nd", "3rd"), latest_numbers):
        pkey = _key(number)
        engines, routes = [], []
        for label, number_cols, route_cols in ENGINES:
            hits: List[str] = []
            for col in number_cols:
                if col in detail_df.columns:
                    hits += _split_numbers(row.get(col))
            if any(_key(h) == pkey for h in hits):
                engines.append(label)
                for rc in route_cols:
                    if rc in detail_df.columns:
                        for snippet in _route_snippets(row.get(rc), pkey):
                            routes.append(f"{label}: {snippet}")
        records.append({
            "Hadiah": prize,
            "No": _pad4(number),
            "Dijana oleh": ", ".join(engines) if engines else "Tiada engine menjana",
            "Bil engine": len(engines),
            "Laluan": " | ".join(dict.fromkeys(routes)) if routes else "-",
        })
    return {
        "source_draw": str(row.get("Source Draw", "")),
        "source_result": str(row.get("Source Result", "")),
        "table": pd.DataFrame(records),
    }


def summary_line(table: pd.DataFrame) -> str:
    covered = int((table["Bil engine"] > 0).sum())
    return (f"{covered} daripada 3 nombor dijana oleh sekurang-kurangnya satu engine "
            "(padanan box: digit disusun semula dikira sama).")


# --------------------------------------------------------------------------
# Nama fail yang kemas
# --------------------------------------------------------------------------
def backtest_filename(latest_draw_no, draws: int, ext: str = "xlsx") -> str:
    """Contoh: Rumah_A_Backtest_Draw620326_30draw.xlsx"""
    draw = re.sub(r"\D", "", str(latest_draw_no)) or "terkini"
    return f"Rumah_A_Backtest_Draw{draw}_{int(draws)}draw.{ext}"
