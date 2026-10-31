
import streamlit as st
import json
import re
import streamlit.components.v1 as components
import pandas as pd
import requests
import base64
from collections import Counter
from itertools import combinations
from pathlib import Path
from io import BytesIO
import math

# Modul backtest jujur (bandingan dengan peluang rawak) - fail berasingan.
from backtest_baseline import (
    bridge_vs_chance,
    prepare_draws,
    run_walk_forward,
    verdict as baseline_verdict,
)
from ui_theme import (
    apply_theme,
    hero_html,
    info_row_html,
    number_chips_html,
    origin_html,
    signal_tiles_html,
)
from latest_origin import (
    backtest_filename,
    explain_latest_numbers,
    summary_line as origin_summary_line,
)
from ranking_engine import (
    build_bridge_pair_priority_dynamic,
    pair_ranking_diagnostics,
    rank_candidates_consensus,
    rank_pair_numbers,
    route_chance,
    route_lift,
)


def _pad4(value):
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return "".join(char for char in text if char.isdigit()).zfill(4)[-4:]


def _key4(value):
    return "".join(sorted(_pad4(value)))


def _pair_key(value):
    return "".join(sorted(str(value).zfill(2)[-2:]))


@st.cache_data(show_spinner=False)
def build_2d_missing_first_digit_engine(
    history, first, second, third, bridge_v1_df, bridge_v2_df, lookback=100
):
    """2D hadiah kedua + missing + satu digit hadiah pertama."""
    second_positions = list(combinations(range(4), 2))
    first_positions = range(4)
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    route_hits = Counter()
    second_draw_hits = Counter()
    first_draw_hits = Counter()
    transitions = 0

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_top3 = [
            _pad4(frame.iloc[index][column])
            for column in ("first", "second", "third")
        ]
        missing_digits = sorted(set("0123456789") - set("".join(source_top3)))
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        second_hit_now = set()
        first_hit_now = set()
        for left, right in second_positions:
            second_label = f"{left + 1}+{right + 1}"
            duo = source_second[left] + source_second[right]
            for first_index in first_positions:
                hit = any(
                    _key4(f"{duo}{missing}{source_first[first_index]}") in targets
                    for missing in missing_digits
                )
                if hit:
                    route_hits[(second_label, first_index + 1)] += 1
                    second_hit_now.add(second_label)
                    first_hit_now.add(first_index + 1)
        for label in second_hit_now:
            second_draw_hits[label] += 1
        for position in first_hit_now:
            first_draw_hits[position] += 1
        transitions += 1

    second_audit = pd.DataFrame([
        {
            "Kedudukan 2D": f"{left + 1}+{right + 1}",
            "Hit Draw": second_draw_hits[f"{left + 1}+{right + 1}"],
            "Draw Diuji": transitions,
            "Hit Rate %": round(
                second_draw_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1
            ) if transitions else 0,
        }
        for left, right in second_positions
    ]).sort_values(["Hit Draw", "Kedudukan 2D"], ascending=[False, True]).reset_index(drop=True)

    first_audit = pd.DataFrame([
        {
            "Kedudukan Digit 1st": position,
            "Hit Draw": first_draw_hits[position],
            "Draw Diuji": transitions,
            "Hit Rate %": round(first_draw_hits[position] / transitions * 100, 1)
            if transitions else 0,
        }
        for position in range(1, 5)
    ]).sort_values(
        ["Hit Draw", "Kedudukan Digit 1st"], ascending=[False, True]
    ).reset_index(drop=True)

    joint_audit = pd.DataFrame([
        {
            "Kedudukan 2D": f"{left + 1}+{right + 1}",
            "Kedudukan Digit 1st": first_position,
            "Hit Draw": route_hits[(f"{left + 1}+{right + 1}", first_position)],
            "Draw Diuji": transitions,
            "Hit Rate %": round(
                route_hits[(f"{left + 1}+{right + 1}", first_position)]
                / transitions * 100, 1
            ) if transitions else 0,
        }
        for left, right in second_positions
        for first_position in range(1, 5)
    ]).sort_values(
        ["Hit Draw", "Kedudukan 2D", "Kedudukan Digit 1st"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    best_second_hits = int(second_audit["Hit Draw"].max()) if not second_audit.empty else 0
    best_first_hits = int(first_audit["Hit Draw"].max()) if not first_audit.empty else 0
    selected_second = second_audit.loc[
        second_audit["Hit Draw"].eq(best_second_hits), "Kedudukan 2D"
    ].astype(str).tolist()
    selected_first = first_audit.loc[
        first_audit["Hit Draw"].eq(best_first_hits), "Kedudukan Digit 1st"
    ].astype(int).tolist()

    current_first = _pad4(first)
    current_second = _pad4(second)
    current_top3 = [_pad4(first), _pad4(second), _pad4(third)]
    current_missing = sorted(set("0123456789") - set("".join(current_top3)))
    bridge_v1 = {
        _key4(number): _pad4(number)
        for number in bridge_v1_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v1_df is not None and not bridge_v1_df.empty else {}
    bridge_v2 = {
        _key4(number): _pad4(number)
        for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v2_df is not None and not bridge_v2_df.empty else {}

    pair_groups = []
    pair_group_lookup = {}
    for left, right in second_positions:
        second_label = f"{left + 1}+{right + 1}"
        duo = current_second[left] + current_second[right]
        duo_key = _pair_key(duo)
        if duo_key not in pair_group_lookup:
            pair_group_lookup[duo_key] = {
                "2D": duo, "Kedudukan": [],
            }
            pair_groups.append(pair_group_lookup[duo_key])
        pair_group_lookup[duo_key]["Kedudukan"].append(second_label)

    all_rows = []
    for pair_group in pair_groups:
        duo = pair_group["2D"]
        second_label = " / ".join(dict.fromkeys(pair_group["Kedudukan"]))
        for first_index in first_positions:
            first_digit = current_first[first_index]
            for missing in current_missing:
                generated = f"{duo}{missing}{first_digit}"
                key = _key4(generated)
                all_rows.append({
                    "Kedudukan 2D": second_label,
                    "2D": duo,
                    "Missing": missing,
                    "Kedudukan Digit 1st": first_index + 1,
                    "Digit 1st": first_digit,
                    "No Terhasil": generated,
                    "Bridge V1": bridge_v1.get(key, ""),
                    "Bridge V2": bridge_v2.get(key, ""),
                })
    all_candidates = pd.DataFrame(all_rows)
    selected_candidates = all_candidates[
        all_candidates["Kedudukan 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_second
            )
        )
        & all_candidates["Kedudukan Digit 1st"].isin(selected_first)
    ].copy() if not all_candidates.empty else all_candidates.copy()
    return {
        "second_audit": second_audit,
        "first_audit": first_audit,
        "joint_audit": joint_audit,
        "selected_second": selected_second,
        "selected_first": selected_first,
        "missing": current_missing,
        "selected": selected_candidates,
        "all": all_candidates,
    }


@st.cache_data(show_spinner=False)
def build_2d_route_signal(history, first, second, third, lookback=100):
    """Pilih laluan 2D semasa melalui padanan keadaan sejarah."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    rows = []

    def occurrence_pairs(first_no, third_no):
        pool = _pad4(first_no) + _pad4(third_no)
        return sorted({
            "".join(sorted((pool[left], pool[right])))
            for left, right in combinations(range(len(pool)), 2)
        })

    def state_values(first_no, second_no, third_no):
        numbers = [_pad4(first_no), _pad4(second_no), _pad4(third_no)]
        return {
            "missing": 10 - len(set("".join(numbers))),
            "second_unique": len(set(numbers[1])),
            "first_unique": len(set(numbers[0])),
            "third_unique": len(set(numbers[2])),
            "repeat_prizes": sum(len(set(number)) < 4 for number in numbers),
            "second_double": int(len(set(numbers[1])) < 4),
        }

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        source_numbers = [source_first, source_second, source_third]
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        missing_digits = sorted(
            set("0123456789") - set("".join(source_numbers))
        )
        suffixes = occurrence_pairs(source_first, source_third)
        missing_keys, first_third_keys = set(), set()
        for left, right in combinations(range(4), 2):
            duo = source_second[left] + source_second[right]
            missing_keys.update(
                _key4(f"{duo}{missing}{first_digit}")
                for missing in missing_digits
                for first_digit in source_first
            )
            first_third_keys.update(_key4(f"{duo}{suffix}") for suffix in suffixes)
        missing_hit = bool(missing_keys & targets)
        first_third_hit = bool(first_third_keys & targets)
        row = state_values(source_first, source_second, source_third)
        row.update({
            "missing_hit": missing_hit,
            "first_third_hit": first_third_hit,
            "missing_exp": route_chance(missing_keys),
            "first_third_exp": route_chance(first_third_keys),
        })
        rows.append(row)

    current = state_values(first, second, third)
    state_groups = [
        ("missing", "second_unique"),
        ("missing", "repeat_prizes"),
        ("missing", "second_double"),
        ("missing", "first_unique", "third_unique"),
    ]
    votes = Counter()
    evidence = []
    for features in state_groups:
        matches = [
            row for row in rows
            if all(row[feature] == current[feature] for feature in features)
        ]
        if len(matches) < 3:
            continue
        missing_rate = sum(row["missing_hit"] for row in matches) / len(matches)
        first_third_rate = sum(
            row["first_third_hit"] for row in matches
        ) / len(matches)
        # Undi guna lift (hit / jangkaan liputan) supaya laluan yang calonnya
        # lebih banyak tidak menang hanya kerana liputan lebih besar.
        missing_lift = route_lift(matches, "missing_hit", "missing_exp")
        first_third_lift = route_lift(matches, "first_third_hit", "first_third_exp")
        if missing_lift > first_third_lift:
            vote = "2D + Missing"
        elif first_third_lift > missing_lift:
            vote = "2D + 1st & 3rd"
        else:
            vote = "Seimbang"
        votes[vote] += 1
        evidence.append({
            "Keadaan": " + ".join(features),
            "Padanan": len(matches),
            "2D + Missing %": round(missing_rate * 100, 1),
            "2D + 1st & 3rd %": round(first_third_rate * 100, 1),
            "Lift Missing": round(missing_lift, 2),
            "Lift 1st&3rd": round(first_third_lift, 2),
            "Signal": vote,
        })

    decisive = {
        name: count for name, count in votes.items() if name != "Seimbang"
    }
    if not decisive:
        signal = "Seimbang"
        support = 0
    else:
        best = max(decisive.values())
        leaders = [name for name, count in decisive.items() if count == best]
        signal = leaders[0] if len(leaders) == 1 else "Seimbang"
        support = best if len(leaders) == 1 else 0
    return {
        "signal": signal,
        "support": support,
        "tested_states": len(evidence),
        "evidence": pd.DataFrame(evidence),
    }


@st.cache_data(show_spinner=False)
def build_2d_first_third_pair_engine(history, first, second, third, lookback=100):
    """2D daripada 2nd + dua digit berdasarkan kemunculan sebenar 1st dan 3rd."""
    second_positions = list(combinations(range(4), 2))
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    position_hits = Counter()
    transitions = 0

    def occurrence_pairs(first_no, third_no):
        pool = _pad4(first_no) + _pad4(third_no)
        return sorted({
            "".join(sorted((pool[left], pool[right])))
            for left, right in combinations(range(len(pool)), 2)
        })

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        suffixes = occurrence_pairs(source_first, source_third)
        target_keys = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        for left, right in second_positions:
            label = f"{left + 1}+{right + 1}"
            duo = source_second[left] + source_second[right]
            if any(_key4(f"{duo}{suffix}") in target_keys for suffix in suffixes):
                position_hits[label] += 1
        transitions += 1

    audit_df = pd.DataFrame([
        {
            "Kedudukan 2D": f"{left + 1}+{right + 1}",
            "Hit Draw": position_hits[f"{left + 1}+{right + 1}"],
            "Draw Diuji": transitions,
            "Hit Rate %": round(
                position_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1
            ) if transitions else 0,
        }
        for left, right in second_positions
    ]).sort_values(["Hit Draw", "Kedudukan 2D"], ascending=[False, True]).reset_index(drop=True)
    best_hits = int(audit_df["Hit Draw"].max()) if not audit_df.empty else 0
    selected_positions = audit_df.loc[
        audit_df["Hit Draw"].eq(best_hits), "Kedudukan 2D"
    ].astype(str).tolist()

    current_second = _pad4(second)
    suffixes = occurrence_pairs(first, third)
    pair_groups = []
    pair_group_lookup = {}
    for left, right in second_positions:
        label = f"{left + 1}+{right + 1}"
        duo = current_second[left] + current_second[right]
        duo_key = _pair_key(duo)
        if duo_key not in pair_group_lookup:
            pair_group_lookup[duo_key] = {"2D": duo, "Kedudukan": []}
            pair_groups.append(pair_group_lookup[duo_key])
        pair_group_lookup[duo_key]["Kedudukan"].append(label)

    rows = []
    for pair_group in pair_groups:
        duo = pair_group["2D"]
        label = " / ".join(dict.fromkeys(pair_group["Kedudukan"]))
        for suffix in suffixes:
            number = f"{duo}{suffix}"
            rows.append({
                "Kedudukan 2D": label,
                "2D": duo,
                "Pair 1st+3rd": suffix,
                "No Terhasil": number,
            })
    all_df = pd.DataFrame(rows)
    selected_df = all_df[
        all_df["Kedudukan 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_positions
            )
        )
    ].copy() if not all_df.empty else all_df.copy()
    return {
        "audit": audit_df,
        "selected_positions": selected_positions,
        "suffixes": suffixes,
        "selected": selected_df,
        "all": all_df,
    }


def _occurrence_pairs_two_prizes(left_prize, right_prize):
    """Pair digit mengikut kemunculan sebenar dalam dua hadiah."""
    pool = _pad4(left_prize) + _pad4(right_prize)
    return sorted({
        "".join(sorted((pool[left], pool[right])))
        for left, right in combinations(range(len(pool)), 2)
    })


def _position_pair_groups(number):
    """Enam kedudukan 2D; pair terbalik/berulang dipaparkan sekali."""
    groups, lookup = [], {}
    number = _pad4(number)
    for left, right in combinations(range(4), 2):
        label = f"{left + 1}+{right + 1}"
        duo = number[left] + number[right]
        duo_key = _pair_key(duo)
        if duo_key not in lookup:
            lookup[duo_key] = {"2D": duo, "Kedudukan": []}
            groups.append(lookup[duo_key])
        lookup[duo_key]["Kedudukan"].append(label)
    return groups


@st.cache_data(show_spinner=False)
def build_1st_missing_digit_engine(
    history, first, second, third, bridge_v1_df, bridge_v2_df, lookback=100
):
    """1st 2D + missing + digit daripada hadiah 2nd atau 3rd."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    positions = list(combinations(range(4), 2))
    position_hits, source_hits, digit_hits, joint_hits = (
        Counter(), Counter(), Counter(), Counter()
    )
    transitions = 0

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        source_numbers = [source_first, source_second, source_third]
        missing_digits = sorted(set("0123456789") - set("".join(source_numbers)))
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        hit_positions, hit_sources, hit_digits = set(), set(), set()
        for left, right in positions:
            position = f"{left + 1}+{right + 1}"
            duo = source_first[left] + source_first[right]
            for source_name, source_number in (
                ("Digit 2nd", source_second), ("Digit 3rd", source_third)
            ):
                for digit_index, digit in enumerate(source_number, start=1):
                    hit = any(
                        _key4(f"{duo}{missing}{digit}") in targets
                        for missing in missing_digits
                    )
                    if hit:
                        joint_hits[(position, source_name, digit_index)] += 1
                        hit_positions.add(position)
                        hit_sources.add(source_name)
                        hit_digits.add((source_name, digit_index))
        for position in hit_positions:
            position_hits[position] += 1
        for source_name in hit_sources:
            source_hits[source_name] += 1
        for source_digit in hit_digits:
            digit_hits[source_digit] += 1
        transitions += 1

    position_audit = pd.DataFrame([{
        "Kedudukan 1st 2D": f"{left + 1}+{right + 1}",
        "Hit Draw": position_hits[f"{left + 1}+{right + 1}"],
        "Draw Diuji": transitions,
        "Hit Rate %": round(
            position_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1
        ) if transitions else 0,
    } for left, right in positions]).sort_values(
        ["Hit Draw", "Kedudukan 1st 2D"], ascending=[False, True]
    ).reset_index(drop=True)
    source_audit = pd.DataFrame([{
        "Sumber Digit": source_name,
        "Hit Draw": source_hits[source_name],
        "Draw Diuji": transitions,
        "Hit Rate %": round(source_hits[source_name] / transitions * 100, 1)
        if transitions else 0,
    } for source_name in ("Digit 2nd", "Digit 3rd")]).sort_values(
        ["Hit Draw", "Sumber Digit"], ascending=[False, True]
    ).reset_index(drop=True)
    digit_audit = pd.DataFrame([{
        "Sumber Digit": source_name,
        "Kedudukan Digit": digit_index,
        "Hit Draw": digit_hits[(source_name, digit_index)],
        "Draw Diuji": transitions,
        "Hit Rate %": round(
            digit_hits[(source_name, digit_index)] / transitions * 100, 1
        ) if transitions else 0,
    } for source_name in ("Digit 2nd", "Digit 3rd")
      for digit_index in range(1, 5)]).sort_values(
        ["Hit Draw", "Sumber Digit", "Kedudukan Digit"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    joint_audit = pd.DataFrame([{
        "Kedudukan 1st 2D": f"{left + 1}+{right + 1}",
        "Sumber Digit": source_name,
        "Kedudukan Digit": digit_index,
        "Hit Draw": joint_hits[(f"{left + 1}+{right + 1}", source_name, digit_index)],
        "Draw Diuji": transitions,
        "Hit Rate %": round(
            joint_hits[(f"{left + 1}+{right + 1}", source_name, digit_index)]
            / transitions * 100, 1
        ) if transitions else 0,
    } for left, right in positions
      for source_name in ("Digit 2nd", "Digit 3rd")
      for digit_index in range(1, 5)]).sort_values(
        ["Hit Draw", "Kedudukan 1st 2D", "Sumber Digit", "Kedudukan Digit"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)

    best_position = int(position_audit["Hit Draw"].max()) if not position_audit.empty else 0
    selected_positions = position_audit.loc[
        position_audit["Hit Draw"].eq(best_position), "Kedudukan 1st 2D"
    ].astype(str).tolist()
    best_source = int(source_audit["Hit Draw"].max()) if not source_audit.empty else 0
    selected_sources = source_audit.loc[
        source_audit["Hit Draw"].eq(best_source), "Sumber Digit"
    ].astype(str).tolist()
    selected_joint = joint_audit[
        joint_audit["Kedudukan 1st 2D"].isin(selected_positions)
        & joint_audit["Sumber Digit"].isin(selected_sources)
    ]
    best_joint = int(selected_joint["Hit Draw"].max()) if not selected_joint.empty else 0
    selected_digits = selected_joint.loc[
        selected_joint["Hit Draw"].eq(best_joint),
        ["Sumber Digit", "Kedudukan Digit"],
    ].drop_duplicates().to_dict("records")

    bridge_v1 = {
        _key4(number): _pad4(number)
        for number in bridge_v1_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v1_df is not None and not bridge_v1_df.empty else {}
    bridge_v2 = {
        _key4(number): _pad4(number)
        for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v2_df is not None and not bridge_v2_df.empty else {}
    current_numbers = [_pad4(first), _pad4(second), _pad4(third)]
    current_missing = sorted(set("0123456789") - set("".join(current_numbers)))
    source_lookup = {"Digit 2nd": current_numbers[1], "Digit 3rd": current_numbers[2]}
    rows = []
    for group in _position_pair_groups(first):
        labels = " / ".join(dict.fromkeys(group["Kedudukan"]))
        for source_name, source_number in source_lookup.items():
            for digit_index, digit in enumerate(source_number, start=1):
                for missing in current_missing:
                    generated = f"{group['2D']}{missing}{digit}"
                    family = _key4(generated)
                    rows.append({
                        "Kedudukan 1st 2D": labels, "1st 2D": group["2D"],
                        "Missing": missing, "Sumber Digit": source_name,
                        "Kedudukan Digit": digit_index, "Digit": digit,
                        "No Terhasil": generated,
                        "Bridge V1": bridge_v1.get(family, ""),
                        "Bridge V2": bridge_v2.get(family, ""),
                    })
    all_df = pd.DataFrame(rows)
    selected_df = all_df[
        all_df["Kedudukan 1st 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_positions
            )
        )
        & all_df.apply(
            lambda row: any(
                row["Sumber Digit"] == item["Sumber Digit"]
                and int(row["Kedudukan Digit"]) == int(item["Kedudukan Digit"])
                for item in selected_digits
            ), axis=1,
        )
    ].copy() if not all_df.empty else all_df.copy()
    return {
        "position_audit": position_audit, "source_audit": source_audit,
        "digit_audit": digit_audit, "joint_audit": joint_audit,
        "selected_positions": selected_positions,
        "selected_sources": selected_sources, "selected_digits": selected_digits,
        "missing": current_missing, "selected": selected_df, "all": all_df,
    }


@st.cache_data(show_spinner=False)
def build_1st_second_third_pair_engine(history, first, second, third, lookback=100):
    """1st 2D + pair digit yang muncul dalam hadiah 2nd dan 3rd."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    positions = list(combinations(range(4), 2))
    position_hits, transitions = Counter(), 0
    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        suffixes = _occurrence_pairs_two_prizes(source_second, source_third)
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        for left, right in positions:
            label = f"{left + 1}+{right + 1}"
            duo = source_first[left] + source_first[right]
            if any(_key4(f"{duo}{suffix}") in targets for suffix in suffixes):
                position_hits[label] += 1
        transitions += 1
    audit_df = pd.DataFrame([{
        "Kedudukan 1st 2D": f"{left + 1}+{right + 1}",
        "Hit Draw": position_hits[f"{left + 1}+{right + 1}"],
        "Draw Diuji": transitions,
        "Hit Rate %": round(
            position_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1
        ) if transitions else 0,
    } for left, right in positions]).sort_values(
        ["Hit Draw", "Kedudukan 1st 2D"], ascending=[False, True]
    ).reset_index(drop=True)
    best_hits = int(audit_df["Hit Draw"].max()) if not audit_df.empty else 0
    selected_positions = audit_df.loc[
        audit_df["Hit Draw"].eq(best_hits), "Kedudukan 1st 2D"
    ].astype(str).tolist()
    suffixes = _occurrence_pairs_two_prizes(second, third)
    rows = []
    for group in _position_pair_groups(first):
        labels = " / ".join(dict.fromkeys(group["Kedudukan"]))
        for suffix in suffixes:
            rows.append({
                "Kedudukan 1st 2D": labels, "1st 2D": group["2D"],
                "Pair 2nd+3rd": suffix,
                "No Terhasil": f"{group['2D']}{suffix}",
            })
    all_df = pd.DataFrame(rows)
    selected_df = all_df[
        all_df["Kedudukan 1st 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_positions
            )
        )
    ].copy() if not all_df.empty else all_df.copy()
    return {
        "audit": audit_df, "selected_positions": selected_positions,
        "suffixes": suffixes, "selected": selected_df, "all": all_df,
    }


@st.cache_data(show_spinner=False)
def build_1st_route_signal(history, first, second, third, lookback=100):
    """Pilih V1 atau V2 bagi laluan 1st 2D mengikut keadaan sejarah semasa."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)

    def state_values(first_no, second_no, third_no):
        numbers = [_pad4(first_no), _pad4(second_no), _pad4(third_no)]
        return {
            "missing": 10 - len(set("".join(numbers))),
            "first_unique": len(set(numbers[0])),
            "second_unique": len(set(numbers[1])),
            "third_unique": len(set(numbers[2])),
            "repeat_prizes": sum(len(set(number)) < 4 for number in numbers),
            "first_double": int(len(set(numbers[0])) < 4),
        }

    rows = []
    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        numbers = [source_first, source_second, source_third]
        missing = sorted(set("0123456789") - set("".join(numbers)))
        suffixes = _occurrence_pairs_two_prizes(source_second, source_third)
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        missing_keys, second_third_keys = set(), set()
        for left, right in combinations(range(4), 2):
            duo = source_first[left] + source_first[right]
            missing_keys.update(
                _key4(f"{duo}{digit}{source_digit}")
                for digit in missing for source_digit in source_third
            )
            second_third_keys.update(_key4(f"{duo}{suffix}") for suffix in suffixes)
        missing_hit = bool(missing_keys & targets)
        second_third_hit = bool(second_third_keys & targets)
        row = state_values(*numbers)
        row.update({
            "missing_hit": missing_hit, "second_third_hit": second_third_hit,
            "missing_exp": route_chance(missing_keys),
            "second_third_exp": route_chance(second_third_keys),
        })
        rows.append(row)

    current = state_values(first, second, third)
    groups = [
        ("missing", "first_unique"), ("missing", "repeat_prizes"),
        ("missing", "first_double"),
        ("missing", "second_unique", "third_unique"),
    ]
    votes, evidence = Counter(), []
    for features in groups:
        matches = [
            row for row in rows
            if all(row[feature] == current[feature] for feature in features)
        ]
        if len(matches) < 3:
            continue
        v1_rate = sum(row["missing_hit"] for row in matches) / len(matches)
        v2_rate = sum(row["second_third_hit"] for row in matches) / len(matches)
        v1_lift = route_lift(matches, "missing_hit", "missing_exp")
        v2_lift = route_lift(matches, "second_third_hit", "second_third_exp")
        vote = "1st 2D + Missing" if v1_lift > v2_lift else (
            "1st 2D + 2nd & 3rd" if v2_lift > v1_lift else "Seimbang"
        )
        votes[vote] += 1
        evidence.append({
            "Keadaan": " + ".join(features), "Padanan": len(matches),
            "1st Missing %": round(v1_rate * 100, 1),
            "1st 2nd&3rd %": round(v2_rate * 100, 1), "Signal": vote,
        })
    decisive = {name: count for name, count in votes.items() if name != "Seimbang"}
    if not decisive:
        signal, support = "Seimbang", 0
    else:
        best = max(decisive.values())
        leaders = [name for name, count in decisive.items() if count == best]
        signal = leaders[0] if len(leaders) == 1 else "Seimbang"
        support = best if len(leaders) == 1 else 0
    return {
        "signal": signal, "support": support,
        "tested_states": len(evidence), "evidence": pd.DataFrame(evidence),
    }


@st.cache_data(show_spinner=False)
def build_3rd_missing_first_digit_engine(
    history, first, second, third, bridge_v1_df, bridge_v2_df, lookback=100
):
    """2D hadiah ketiga + missing + satu digit hadiah pertama."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    position_hits, first_hits, joint_hits = Counter(), Counter(), Counter()
    transitions = 0
    positions = list(combinations(range(4), 2))

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_third = _pad4(frame.iloc[index]["third"])
        source_numbers = [
            _pad4(frame.iloc[index][column])
            for column in ("first", "second", "third")
        ]
        missing_digits = sorted(set("0123456789") - set("".join(source_numbers)))
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        hit_positions, hit_first = set(), set()
        for left, right in positions:
            label = f"{left + 1}+{right + 1}"
            duo = source_third[left] + source_third[right]
            for first_index, first_digit in enumerate(source_first, start=1):
                hit = any(
                    _key4(f"{duo}{missing}{first_digit}") in targets
                    for missing in missing_digits
                )
                if hit:
                    joint_hits[(label, first_index)] += 1
                    hit_positions.add(label)
                    hit_first.add(first_index)
        for label in hit_positions:
            position_hits[label] += 1
        for first_index in hit_first:
            first_hits[first_index] += 1
        transitions += 1

    position_audit = pd.DataFrame([{
        "Kedudukan 3rd 2D": f"{left + 1}+{right + 1}",
        "Hit Draw": position_hits[f"{left + 1}+{right + 1}"],
        "Draw Diuji": transitions,
        "Hit Rate %": round(position_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1)
        if transitions else 0,
    } for left, right in positions]).sort_values(
        ["Hit Draw", "Kedudukan 3rd 2D"], ascending=[False, True]
    ).reset_index(drop=True)
    first_audit = pd.DataFrame([{
        "Kedudukan Digit 1st": position,
        "Hit Draw": first_hits[position],
        "Draw Diuji": transitions,
        "Hit Rate %": round(first_hits[position] / transitions * 100, 1)
        if transitions else 0,
    } for position in range(1, 5)]).sort_values(
        ["Hit Draw", "Kedudukan Digit 1st"], ascending=[False, True]
    ).reset_index(drop=True)
    joint_audit = pd.DataFrame([{
        "Kedudukan 3rd 2D": f"{left + 1}+{right + 1}",
        "Kedudukan Digit 1st": first_position,
        "Hit Draw": joint_hits[(f"{left + 1}+{right + 1}", first_position)],
        "Draw Diuji": transitions,
        "Hit Rate %": round(
            joint_hits[(f"{left + 1}+{right + 1}", first_position)] / transitions * 100, 1
        ) if transitions else 0,
    } for left, right in positions for first_position in range(1, 5)]).sort_values(
        ["Hit Draw", "Kedudukan 3rd 2D", "Kedudukan Digit 1st"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    best_position = int(position_audit["Hit Draw"].max()) if not position_audit.empty else 0
    best_first = int(first_audit["Hit Draw"].max()) if not first_audit.empty else 0
    selected_positions = position_audit.loc[
        position_audit["Hit Draw"].eq(best_position), "Kedudukan 3rd 2D"
    ].astype(str).tolist()
    selected_first = first_audit.loc[
        first_audit["Hit Draw"].eq(best_first), "Kedudukan Digit 1st"
    ].astype(int).tolist()

    current_first, current_third = _pad4(first), _pad4(third)
    current_missing = sorted(
        set("0123456789") - set(_pad4(first) + _pad4(second) + current_third)
    )
    v1 = {
        _key4(number): _pad4(number)
        for number in bridge_v1_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v1_df is not None and not bridge_v1_df.empty else {}
    v2 = {
        _key4(number): _pad4(number)
        for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
    } if bridge_v2_df is not None and not bridge_v2_df.empty else {}
    rows = []
    for group in _position_pair_groups(current_third):
        label = " / ".join(group["Kedudukan"])
        for first_index, first_digit in enumerate(current_first, start=1):
            for missing in current_missing:
                generated = f"{group['2D']}{missing}{first_digit}"
                key = _key4(generated)
                rows.append({
                    "Kedudukan 3rd 2D": label, "2D": group["2D"],
                    "Missing": missing, "Kedudukan Digit 1st": first_index,
                    "Digit 1st": first_digit, "No Terhasil": generated,
                    "Bridge V1": v1.get(key, ""), "Bridge V2": v2.get(key, ""),
                })
    all_df = pd.DataFrame(rows)
    selected_df = all_df[
        all_df["Kedudukan 3rd 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_positions
            )
        ) & all_df["Kedudukan Digit 1st"].isin(selected_first)
    ].copy() if not all_df.empty else all_df.copy()
    return {
        "position_audit": position_audit, "first_audit": first_audit,
        "joint_audit": joint_audit, "selected_positions": selected_positions,
        "selected_first": selected_first, "missing": current_missing,
        "selected": selected_df, "all": all_df,
    }


@st.cache_data(show_spinner=False)
def build_3rd_first_second_pair_engine(history, first, second, third, lookback=100):
    """2D hadiah ketiga + dua digit daripada hadiah pertama dan kedua."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    position_hits, transitions = Counter(), 0
    positions = list(combinations(range(4), 2))
    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        suffixes = _occurrence_pairs_two_prizes(source_first, source_second)
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        for left, right in positions:
            label = f"{left + 1}+{right + 1}"
            duo = source_third[left] + source_third[right]
            if any(_key4(f"{duo}{suffix}") in targets for suffix in suffixes):
                position_hits[label] += 1
        transitions += 1
    audit_df = pd.DataFrame([{
        "Kedudukan 3rd 2D": f"{left + 1}+{right + 1}",
        "Hit Draw": position_hits[f"{left + 1}+{right + 1}"],
        "Draw Diuji": transitions,
        "Hit Rate %": round(position_hits[f"{left + 1}+{right + 1}"] / transitions * 100, 1)
        if transitions else 0,
    } for left, right in positions]).sort_values(
        ["Hit Draw", "Kedudukan 3rd 2D"], ascending=[False, True]
    ).reset_index(drop=True)
    best_hits = int(audit_df["Hit Draw"].max()) if not audit_df.empty else 0
    selected_positions = audit_df.loc[
        audit_df["Hit Draw"].eq(best_hits), "Kedudukan 3rd 2D"
    ].astype(str).tolist()
    suffixes = _occurrence_pairs_two_prizes(first, second)
    rows = []
    for group in _position_pair_groups(third):
        label = " / ".join(group["Kedudukan"])
        for suffix in suffixes:
            rows.append({
                "Kedudukan 3rd 2D": label, "2D": group["2D"],
                "Pair 1st+2nd": suffix,
                "No Terhasil": f"{group['2D']}{suffix}",
            })
    all_df = pd.DataFrame(rows)
    selected_df = all_df[
        all_df["Kedudukan 3rd 2D"].apply(
            lambda value: any(
                position in [part.strip() for part in str(value).split("/")]
                for position in selected_positions
            )
        )
    ].copy() if not all_df.empty else all_df.copy()
    return {
        "audit": audit_df, "selected_positions": selected_positions,
        "suffixes": suffixes, "selected": selected_df, "all": all_df,
    }


@st.cache_data(show_spinner=False)
def build_3rd_route_signal(history, first, second, third, lookback=100):
    """Pilih antara dua laluan 3rd sahaja; laluan 2nd tidak disentuh."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    rows = []

    def state_values(first_no, second_no, third_no):
        numbers = [_pad4(first_no), _pad4(second_no), _pad4(third_no)]
        return {
            "missing": 10 - len(set("".join(numbers))),
            "first_unique": len(set(numbers[0])),
            "second_unique": len(set(numbers[1])),
            "third_unique": len(set(numbers[2])),
            "repeat_prizes": sum(len(set(number)) < 4 for number in numbers),
            "third_double": int(len(set(numbers[2])) < 4),
        }

    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        numbers = [source_first, source_second, source_third]
        targets = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        missing = sorted(set("0123456789") - set("".join(numbers)))
        suffixes = _occurrence_pairs_two_prizes(source_first, source_second)
        missing_keys, first_second_keys = set(), set()
        for left, right in combinations(range(4), 2):
            duo = source_third[left] + source_third[right]
            missing_keys.update(
                _key4(f"{duo}{digit}{first_digit}")
                for digit in missing for first_digit in source_first
            )
            first_second_keys.update(_key4(f"{duo}{suffix}") for suffix in suffixes)
        missing_hit = bool(missing_keys & targets)
        first_second_hit = bool(first_second_keys & targets)
        row = state_values(*numbers)
        row.update({
            "missing_hit": missing_hit, "first_second_hit": first_second_hit,
            "missing_exp": route_chance(missing_keys),
            "first_second_exp": route_chance(first_second_keys),
        })
        rows.append(row)

    current = state_values(first, second, third)
    groups = [
        ("missing", "third_unique"),
        ("missing", "repeat_prizes"),
        ("missing", "third_double"),
        ("missing", "first_unique", "second_unique"),
    ]
    votes, evidence = Counter(), []
    for features in groups:
        matches = [
            row for row in rows
            if all(row[feature] == current[feature] for feature in features)
        ]
        if len(matches) < 3:
            continue
        missing_rate = sum(row["missing_hit"] for row in matches) / len(matches)
        first_second_rate = sum(row["first_second_hit"] for row in matches) / len(matches)
        missing_lift = route_lift(matches, "missing_hit", "missing_exp")
        first_second_lift = route_lift(matches, "first_second_hit", "first_second_exp")
        if missing_lift > first_second_lift:
            vote = "3rd 2D + Missing"
        elif first_second_lift > missing_lift:
            vote = "3rd 2D + 1st & 2nd"
        else:
            vote = "Seimbang"
        votes[vote] += 1
        evidence.append({
            "Keadaan": " + ".join(features), "Padanan": len(matches),
            "3rd 2D + Missing %": round(missing_rate * 100, 1),
            "3rd 2D + 1st & 2nd %": round(first_second_rate * 100, 1),
            "Signal": vote,
        })
    decisive = {name: count for name, count in votes.items() if name != "Seimbang"}
    if not decisive:
        signal, support = "Seimbang", 0
    else:
        best = max(decisive.values())
        leaders = [name for name, count in decisive.items() if count == best]
        signal = leaders[0] if len(leaders) == 1 else "Seimbang"
        support = best if len(leaders) == 1 else 0
    return {
        "signal": signal, "support": support,
        "tested_states": len(evidence), "evidence": pd.DataFrame(evidence),
    }


@st.cache_data(show_spinner=False)
def build_first_third_extended_audit(history, first, second, third, lookback=100):
    """Audit digit, pair pelengkap dan gabungannya dengan kedudukan 2D."""
    frame = history.reset_index(drop=True) if history is not None else pd.DataFrame()
    start = max(0, len(frame) - int(lookback) - 1)
    stop = max(0, len(frame) - 1)
    second_positions = list(combinations(range(4), 2))

    def occurrence_pairs(first_no, third_no):
        pool = _pad4(first_no) + _pad4(third_no)
        return sorted({
            "".join(sorted((pool[left], pool[right])))
            for left, right in combinations(range(len(pool)), 2)
        })

    records = []
    for index in range(start, stop):
        source_first = _pad4(frame.iloc[index]["first"])
        source_second = _pad4(frame.iloc[index]["second"])
        source_third = _pad4(frame.iloc[index]["third"])
        pool = source_first + source_third
        suffixes = occurrence_pairs(source_first, source_third)
        target_keys = {
            _key4(frame.iloc[index + 1][column])
            for column in ("first", "second", "third")
        }
        hit_positions, hit_pairs, hit_digits, hit_joint = set(), set(), set(), set()
        for left, right in second_positions:
            position = f"{left + 1}+{right + 1}"
            duo = source_second[left] + source_second[right]
            for suffix in suffixes:
                if _key4(f"{duo}{suffix}") not in target_keys:
                    continue
                hit_positions.add(position)
                hit_pairs.add(suffix)
                hit_digits.update(suffix)
                hit_joint.add((position, suffix))
        records.append({
            "Available Digits": set(pool),
            "Available Pairs": set(suffixes),
            "Hit Positions": hit_positions,
            "Hit Pairs": hit_pairs,
            "Hit Digits": hit_digits,
            "Hit Joint": hit_joint,
        })

    current_digits = sorted(set(_pad4(first) + _pad4(third)))
    current_pairs = occurrence_pairs(first, third)
    windows = [10, 20, 30, 50, 100]

    engine_position_audit = build_2d_first_third_pair_engine(
        history, first, second, third, lookback=lookback
    )["audit"]
    best_position_hits = (
        int(engine_position_audit["Hit Draw"].max())
        if not engine_position_audit.empty else 0
    )
    selected_positions = engine_position_audit.loc[
        engine_position_audit["Hit Draw"].eq(best_position_hits), "Kedudukan 2D"
    ].astype(str).tolist()

    def recent_count(predicate, window):
        subset = records[-min(window, len(records)):] if records else []
        return sum(1 for record in subset if predicate(record))

    digit_rows = []
    for digit in current_digits:
        exposure = sum(digit in record["Available Digits"] for record in records)
        hit_all = sum(digit in record["Hit Digits"] for record in records)
        hit_selected = sum(
            any(
                position in selected_positions and digit in suffix
                for position, suffix in record["Hit Joint"]
            )
            for record in records
        )
        row = {
            "Digit": digit,
            "Exposure": exposure,
            "Hit Semua 2D": hit_all,
            "Rate Semua %": round(hit_all / exposure * 100, 1) if exposure else 0,
            "Hit Kedudukan Utama": hit_selected,
            "Rate Utama %": round(hit_selected / exposure * 100, 1) if exposure else 0,
        }
        for window in windows:
            row[f"Hit {window}"] = recent_count(
                lambda record, d=digit: d in record["Hit Digits"], window
            )
        digit_rows.append(row)
    digit_audit = pd.DataFrame(digit_rows).sort_values(
        ["Hit Kedudukan Utama", "Hit Semua 2D", "Rate Semua %", "Digit"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    pair_rows = []
    for suffix in current_pairs:
        exposure = sum(suffix in record["Available Pairs"] for record in records)
        hit_all = sum(suffix in record["Hit Pairs"] for record in records)
        hit_selected = sum(
            any(
                position in selected_positions and hit_suffix == suffix
                for position, hit_suffix in record["Hit Joint"]
            )
            for record in records
        )
        row = {
            "Pair Digit": suffix,
            "Exposure": exposure,
            "Hit Semua 2D": hit_all,
            "Rate Semua %": round(hit_all / exposure * 100, 1) if exposure else 0,
            "Hit Kedudukan Utama": hit_selected,
            "Rate Utama %": round(hit_selected / exposure * 100, 1) if exposure else 0,
        }
        for window in windows:
            row[f"Hit {window}"] = recent_count(
                lambda record, p=suffix: p in record["Hit Pairs"], window
            )
        pair_rows.append(row)
    pair_audit = pd.DataFrame(pair_rows).sort_values(
        ["Hit Kedudukan Utama", "Hit Semua 2D", "Rate Semua %", "Pair Digit"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    joint_rows = []
    current_second = _pad4(second)
    for left, right in second_positions:
        position = f"{left + 1}+{right + 1}"
        current_duo = current_second[left] + current_second[right]
        for suffix in current_pairs:
            exposure = sum(suffix in record["Available Pairs"] for record in records)
            hits = sum((position, suffix) in record["Hit Joint"] for record in records)
            joint_rows.append({
                "Kedudukan 2D": position,
                "Pair Digit": suffix,
                "Full No": f"{current_duo}{suffix}",
                "Exposure": exposure,
                "Hit Draw": hits,
                "Hit Rate %": round(hits / exposure * 100, 1) if exposure else 0,
            })
    joint_audit = pd.DataFrame(joint_rows).sort_values(
        ["Hit Draw", "Hit Rate %", "Kedudukan 2D", "Pair Digit"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    def leaders(frame, hit_column, label_column):
        if frame.empty:
            return []
        best = int(frame[hit_column].max())
        return frame.loc[frame[hit_column].eq(best), label_column].astype(str).tolist()

    return {
        "selected_positions": selected_positions,
        "digit_audit": digit_audit,
        "pair_audit": pair_audit,
        "joint_audit": joint_audit,
        "top_digit_all": leaders(digit_audit, "Hit Semua 2D", "Digit"),
        "top_digit_selected": leaders(digit_audit, "Hit Kedudukan Utama", "Digit"),
        "top_pair_all": leaders(pair_audit, "Hit Semua 2D", "Pair Digit"),
        "top_pair_selected": leaders(pair_audit, "Hit Kedudukan Utama", "Pair Digit"),
    }


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
        style="border:0;border-radius:12px;background:#0F4BC4;color:#fff;padding:10px 16px;font-size:14px;font-weight:700;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;margin-right:8px;cursor:pointer;">
            {label}
        </button>
        <span id="msg_{key_name}" style="color:#075E41;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;font-size:14px;font-weight:700;margin-left:8px;"></span>
        """,
        height=48
    )

st.set_page_config(page_title="Rumah A Predictor", page_icon="🎯", layout="wide")
apply_theme(st)


def show_numbers(numbers, key_name, highlight=0):
    """Nombor sebagai cip besar yang mudah dibaca, dengan butang Salin."""
    items = [str(n).strip() for n in numbers if str(n).strip()]
    st.markdown(number_chips_html(items, highlight=highlight), unsafe_allow_html=True)
    if items:
        safe_key = re.sub(r"[^A-Za-z0-9_]", "_", f"num_{key_name}")
        copy_button_clean("📋 Salin", "  ".join(items), safe_key)


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
st.markdown(
    hero_html(
        last["draw_no"], last["draw_date"],
        pad4(last["first"]), pad4(last["second"]), pad4(last["third"]),
        sync_active=(token_status == "Aktif"), source=history_source_label,
    ),
    unsafe_allow_html=True,
)


# -----------------------------
# V14: History Manager Lengkap
# -----------------------------


origin_box = st.container()
main_box = st.container()

st.markdown('<div class="rap-section-kicker">Alat & Data</div>', unsafe_allow_html=True)
tools_tabs = st.tabs(["📚 Sejarah Keputusan", "🧪 Ujian & Backtest"])

with tools_tabs[0]:
    with st.container():
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


def unordered_digit_key4(n):
    """Kunci semakan hit tanpa susunan; tidak digunakan untuk memilih calon."""
    try:
        return "".join(sorted(pad4(n)))
    except Exception:
        return ""


def pair_digit_key(pair):
    """Samakan pair terbalik, contohnya 13 dan 31."""
    return "".join(sorted(str(pair).zfill(2)[-2:]))


def build_current_2d_ranking(history, first, second, third, lookback=100):
    """Ranking semua pair semasa berdasarkan kadar pair berulang ke next draw."""
    original_cols = ["1stPrizeNo", "2ndPrizeNo", "3rdPrizeNo"]
    internal_cols = ["first", "second", "third"]

    def row_pairs(values):
        found = []
        for value in values:
            number = pad4(value)
            for left, right in combinations(range(4), 2):
                pair = pair_digit_key(number[left] + number[right])
                if pair not in found:
                    found.append(pair)
        return found

    current_pairs = row_pairs([first, second, third])
    if history is None or history.empty:
        return current_pairs

    if all(column in history.columns for column in internal_cols):
        prize_cols = internal_cols
    elif all(column in history.columns for column in original_cols):
        prize_cols = original_cols
    else:
        return current_pairs

    frame = history.copy()
    draw_column = "draw_no" if "draw_no" in frame.columns else "DrawNo"
    if draw_column in frame.columns:
        frame["_DrawSort"] = pd.to_numeric(frame[draw_column], errors="coerce")
        frame = frame.sort_values("_DrawSort", kind="stable")
    frame = frame.dropna(subset=prize_cols).reset_index(drop=True)
    historical_pairs = [
        set(row_pairs(row))
        for row in frame[prize_cols].itertuples(index=False, name=None)
    ]
    if len(historical_pairs) < 2:
        return current_pairs

    current_key = tuple(pad4(value) for value in (first, second, third))
    last_key = tuple(pad4(frame.iloc[-1][column]) for column in prize_cols)
    # Jika keputusan semasa sudah berada dalam history, jangan gunakan transisi
    # yang berakhir pada keputusan itu untuk menilai pair keputusan yang sama.
    end = len(historical_pairs) - 2 if last_key == current_key else len(historical_pairs) - 1
    start = max(0, end - int(lookback))
    transitions = [
        (historical_pairs[index], historical_pairs[index + 1])
        for index in range(start, end)
    ]

    rows = []
    for original_order, pair in enumerate(current_pairs):
        exposure = sum(pair in source for source, _ in transitions)
        hits = sum(pair in source and pair in target for source, target in transitions)
        rate = hits / exposure if exposure else 0.0
        rows.append((pair, rate, hits, exposure, original_order))
    rows.sort(key=lambda item: (-item[1], -item[2], item[4]))
    return [pair for pair, _, _, _, _ in rows]


def sort_match_numbers_by_2d(numbers, pair_ranking):
    """Susun calon Match mengikut pair semasa paling tinggi yang dikandunginya."""
    rank = {pair: index for index, pair in enumerate(pair_ranking)}

    def number_score(item):
        original_order, number = item
        value = pad4(number)
        number_pairs = {
            pair_digit_key(value[left] + value[right])
            for left, right in combinations(range(4), 2)
        }
        best_rank = min(
            (rank[pair] for pair in number_pairs if pair in rank),
            default=len(rank),
        )
        return best_rank, original_order

    return [
        number for _, number in sorted(enumerate(numbers), key=number_score)
    ]


def keep_first_pair_orientation(pair_rows):
    """Kekalkan orientasi pair yang muncul dahulu sahaja."""
    kept = []
    seen = set()
    for row in pair_rows:
        key = pair_digit_key(row.get("Pair", ""))
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def build_bridge_model_v31_9(first, second, third):
    import pandas as pd
    nums=[pad4(first),pad4(second),pad4(third)]
    existing_digits=sorted(set("".join(nums)))
    missing_digits=sorted(set("0123456789")-set(existing_digits))
    pair_rows=[]; base_pairs=[]
    number_meta={}
    bridge_order=[]

    for label,no in zip(["1st","2nd","3rd"],nums):
        for ptype,pair in zip(["Front","Middle","Back"],[no[:2],no[1:3],no[2:4]]):
            base_pairs.append(pair)
            pair_rows.append({"Source":label,"No":no,"Pair Type":ptype,"Pair":pair})

    pair_rows = keep_first_pair_orientation(pair_rows)
    base_pairs = [row["Pair"] for row in pair_rows]

    for row in pair_rows:
        pair=row["Pair"]
        src=row["Source"]
        ptype=row["Pair Type"]
        for md in missing_digits:
            for ed in existing_digits:
                # V31.21: ikut tertib pair asal.
                # Contoh 82 + 7 + 6 = 8276, bukan canonical 2678 untuk paparan.
                display_no = f"{pair}{md}{ed}"
                if len(display_no)==4 and display_no.isdigit():
                    if display_no not in number_meta:
                        number_meta[display_no]={
                            "Display No":display_no,
                            "Formula List":[],
                            "Base Pairs":set(),
                            "Sources":set(),
                            "Pair Types":set(),
                            "Missing Digits":set(),
                            "Existing Digits":set(),
                        }
                        bridge_order.append(display_no)

                    formula=f"{pair}+{md}+{ed}"
                    number_meta[display_no]["Formula List"].append(formula)
                    number_meta[display_no]["Base Pairs"].add(pair)
                    number_meta[display_no]["Sources"].add(src)
                    number_meta[display_no]["Pair Types"].add(ptype)
                    number_meta[display_no]["Missing Digits"].add(md)
                    number_meta[display_no]["Existing Digits"].add(ed)

    rows=[]
    for order_idx, display_no in enumerate(bridge_order, start=1):
        meta = number_meta[display_no]
        rows.append({
            "No": meta["Display No"],
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
    pair_rows = keep_first_pair_orientation(pair_rows)
    base_pairs = [row["Pair"] for row in pair_rows]

    number_meta = {}
    def add_candidate(pair, d1, d2, mode, source, pair_type):
        display_no = f"{pair}{d1}{d2}"
        meta = number_meta.setdefault(display_no, {
            "No": display_no, "Modes": set(), "Base Pairs": set(),
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
    for order, meta in enumerate(number_meta.values(), 1):
        rows.append({
            "No": meta["No"], "Order": order,
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
def build_bridge_pair_priority(history, first, second, third, lookback=100, version="both"):
    """
    Ranking pair dinamik (ranking_engine): skor = peluang rawak semasa x lift
    berpemberat susut-masa. Susunan berubah mengikut keadaan draw terkini.
    version: "both" | "V1" | "V2".
    """
    return build_bridge_pair_priority_dynamic(
        history, first, second, third, lookback=lookback, version=version
    )


def build_chart_3d_signal_v31_39(first, second, third, bridge_v1_df=None, bridge_v2_df=None):
    """Carta ringan: Menegak/L + Bridge sahaja, tanpa imbasan bentuk Tetris 4D."""
    numbers = [pad4(first), pad4(second), pad4(third)]
    digit_sums = [sum(int(digit) for digit in number) for number in numbers]
    digit_roots = [0 if value == 0 else 1 + (value - 1) % 9 for value in digit_sums]
    total_sum = str(sum(digit_sums))
    root_sum = str(sum(digit_roots))
    cross_rows = [
        "".join(str(int(top_digit) + int(bottom_digit)) for bottom_digit in root_sum)
        for top_digit in total_sum
    ]
    final_row = str(sum(int(digit) for digit in total_sum)) + str(
        sum(int(digit) for digit in root_sum)
    )
    derived_rows = cross_rows + [final_row]
    chart_rows = [total_sum, root_sum] + derived_rows

    three_d_rows, seen = [], set()
    max_width = max(len(row) for row in derived_rows)
    for column in range(max_width):
        if all(column < len(row) for row in derived_rows):
            anchor = "".join(row[column] for row in derived_rows)
            key = ("Menegak", anchor)
            if len(anchor) == 3 and key not in seen:
                seen.add(key)
                three_d_rows.append({"Pilihan": "Menegak", "3D": anchor})
    for row_index in range(len(derived_rows) - 1):
        top_row, bottom_row = derived_rows[row_index], derived_rows[row_index + 1]
        for column in range(min(len(top_row), len(bottom_row)) - 1):
            choices = [
                ("L Kiri", top_row[column] + bottom_row[column] + bottom_row[column + 1]),
                ("L Kanan", top_row[column + 1] + bottom_row[column + 1] + bottom_row[column]),
            ]
            # Lengkapkan orientasi L atas pada baris campur-silang sahaja.
            # Blok 13 / 12 menghasilkan 113; baris jumlah akhir tidak diperluas.
            if row_index < len(cross_rows) - 1:
                upper_l = top_row[column] + bottom_row[column] + top_row[column + 1]
                if (
                    upper_l not in {anchor for _, anchor in choices}
                    and not any(existing_anchor == upper_l for _, existing_anchor in seen)
                ):
                    choices.append(("L Atas", upper_l))
            for label, anchor in choices:
                if any(
                    existing_label != "Menegak" and existing_anchor == anchor
                    for existing_label, existing_anchor in seen
                ):
                    continue
                key = (label, anchor)
                if key not in seen:
                    seen.add(key)
                    three_d_rows.append({"Pilihan": label, "3D": anchor})
    three_d_df = pd.DataFrame(three_d_rows, columns=["Pilihan", "3D"])

    def bridge_lookup(frame):
        numbers = []
        if frame is None or frame.empty:
            return numbers
        for _, row in frame.iterrows():
            number = pad4(row.get("No", ""))
            if number and number not in numbers:
                numbers.append(number)
        return numbers

    v1_numbers = bridge_lookup(bridge_v1_df)
    v2_numbers = bridge_lookup(bridge_v2_df)
    confirmed_rows = []
    for _, choice in three_d_df.iterrows():
        anchor = str(choice["3D"])
        for bridge_name, bridge_numbers in (
            ("V1", v1_numbers),
            ("V2", v2_numbers),
        ):
            for number in bridge_numbers:
                if Counter(anchor) - Counter(number):
                    continue
                confirmed_rows.append({
                    "Pilihan": str(choice["Pilihan"]),
                    "3D": anchor,
                    "No": number,
                    "Bridge": bridge_name,
                })
    confirmed_df = pd.DataFrame(
        confirmed_rows,
        columns=["Pilihan", "3D", "No", "Bridge"],
    )
    if not confirmed_df.empty:
        confirmed_df = (
            confirmed_df.drop_duplicates()
            .sort_values(["Pilihan", "3D", "Bridge", "No"])
            .reset_index(drop=True)
        )

    vertical_values = three_d_df[three_d_df["Pilihan"] == "Menegak"]["3D"].tolist()
    l_values = three_d_df[three_d_df["Pilihan"] != "Menegak"]["3D"].tolist()
    chart_text = (
        "🧩 Rumah A Predictor - Carta 3D V2\n\n"
        f"Top 3: {' / '.join(numbers)}\n"
        f"Jumlah Digit: {' / '.join(str(value) for value in digit_sums)}\n"
        f"Digital Root: {' / '.join(str(value) for value in digit_roots)}\n"
        f"Asas: {total_sum} / {root_sum}\n\n"
        + "\n".join(chart_rows)
        + f"\n\nPilihan Menegak: {' / '.join(vertical_values) or 'Tiada'}"
        + f"\nPilihan L: {' / '.join(l_values) or 'Tiada'}"
    )
    choice_lines = [
        "🎯 Rumah A Predictor - Pilihan Carta 3D + Bridge",
        "",
        f"Pilihan Menegak: {' / '.join(vertical_values) or 'Tiada'}",
        f"Pilihan L: {' / '.join(l_values) or 'Tiada'}",
        f"Jumlah 3D Carta + Bridge: {len(confirmed_df)}",
    ]
    if confirmed_df.empty:
        choice_lines.extend(["", "Tiada pilihan Carta 3D yang disahkan Bridge."])
    else:
        choice_lines.extend(["", "3D Carta + Bridge:"])
        for _, row in confirmed_df.iterrows():
            choice_lines.append(
                f'{row["Pilihan"]} {row["3D"]} | {row["Bridge"]} | {row["No"]}'
            )
    meta = {
        "Rows": chart_rows,
        "3D Choices": three_d_df,
        "3D Confirmed": confirmed_df,
    }
    return chart_text, "\n".join(choice_lines), meta


@st.cache_data(show_spinner=False)


@st.cache_data(show_spinner=False)
def run_backtest_bridge_dde_lite_v31_24_5(history_df, test_draws=30):
    import json
    import time
    t0 = time.perf_counter()
    if history_df is None or history_df.empty or len(history_df) < 2:
        return pd.DataFrame(), pd.DataFrame()
    h = history_df.copy().reset_index(drop=True)
    for col in ("first", "second", "third"):
        h[col] = h[col].apply(pad4)
    latest_idx = len(h) - 1
    count = max(1, min(int(test_draws), latest_idx + 1))
    start_idx = max(0, latest_idx - count + 1)
    cache_path = Path(".backtest_row_cache_v31_55_bridge_solo.json")
    cache = {}
    try:
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("version") == "v31.55-bridge-solo":
                cache = payload.get("rows", {})
    except Exception:
        cache = {}
    rows = []
    for idx in range(start_idx, latest_idx + 1):
        source = h.iloc[idx]
        first, second, third = (pad4(source[c]) for c in ("first", "second", "third"))
        if idx + 1 < len(h):
            nxt = h.iloc[idx + 1]
            next_sig = "|".join([str(nxt.get("draw_no", ""))] + [pad4(nxt[c]) for c in ("first", "second", "third")])
        else:
            nxt, next_sig = None, "PENDING"
        key = "|".join([str(source.get("draw_no", idx)), first, second, third, next_sig])
        if key in cache:
            rows.append(cache[key])
            continue
        _, v1_df, _ = build_bridge_model_v31_9(first, second, third)
        _, v2_df, _ = build_bridge_engine_v2_pair_double_digit(first, second, third)
        v1_list = v1_df["No"].astype(str).tolist() if not v1_df.empty else []
        v2_list = v2_df["No"].astype(str).tolist() if not v2_df.empty else []
        v1_digit_keys = {unordered_digit_key4(x) for x in v1_list}
        v2_digit_keys = {unordered_digit_key4(x) for x in v2_list}
        v2_missing = {
            unordered_digit_key4(x)
            for x in v2_df[v2_df["Mode"].str.contains("2 Missing", regex=False)]["No"].astype(str)
        } if not v2_df.empty else set()
        v2_existing = {
            unordered_digit_key4(x)
            for x in v2_df[v2_df["Mode"].str.contains("2 Existing", regex=False)]["No"].astype(str)
        } if not v2_df.empty else set()
        if nxt is None:
            next_draw, next_result = "", "Belum ada next draw"
            actual_nums, actual_digit_keys = [], []
            status = "PENDING"
        else:
            actual_nums = [pad4(nxt[c]) for c in ("first", "second", "third")]
            actual_digit_keys = [unordered_digit_key4(x) for x in actual_nums]
            next_draw, next_result, status = str(nxt.get("draw_no", "")), " / ".join(actual_nums), "DONE"
        v1_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v1_digit_keys]
        v2_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_digit_keys]
        missing_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_missing]
        existing_hits = [n for n, key in zip(actual_nums, actual_digit_keys) if key in v2_existing]
        union_hits = list(dict.fromkeys(v1_hits + v2_hits))

        # 1st 2D + missing + digit daripada 2nd atau 3rd.
        source_top3 = [first, second, third]
        carry_missing = sorted(set("0123456789") - set("".join(source_top3)))
        first_missing_keys = {"Digit 2nd": set(), "Digit 3rd": set()}
        first_missing_positions = {"Digit 2nd": [], "Digit 3rd": []}
        first_missing_routes = {"Digit 2nd": [], "Digit 3rd": []}
        for left, right in combinations(range(4), 2):
            position = f"{left + 1}+{right + 1}"
            duo = first[left] + first[right]
            for source_name, source_number in (
                ("Digit 2nd", second), ("Digit 3rd", third)
            ):
                for digit_position, digit in enumerate(source_number, start=1):
                    for missing_digit in carry_missing:
                        generated = f"{duo}{missing_digit}{digit}"
                        generated_key = unordered_digit_key4(generated)
                        first_missing_keys[source_name].add(generated_key)
                        for target_number, target_key in zip(actual_nums, actual_digit_keys):
                            if generated_key != target_key:
                                continue
                            first_missing_positions[source_name].append(position)
                            first_missing_routes[source_name].append(
                                f"{position} x {source_name}-{digit_position} | "
                                f"{generated} -> {target_number}"
                            )
        first_missing_hits = {
            source_name: list(dict.fromkeys(
                number for number, target_key in zip(actual_nums, actual_digit_keys)
                if target_key in keys
            )) for source_name, keys in first_missing_keys.items()
        }
        first_missing_bridge_hits = {
            source_name: list(dict.fromkeys(
                number for number, target_key in zip(actual_nums, actual_digit_keys)
                if target_key in keys and target_key in v1_digit_keys
            )) for source_name, keys in first_missing_keys.items()
        }

        # 1st 2D + dua digit yang benar-benar muncul dalam 2nd dan 3rd.
        second_third_suffixes = _occurrence_pairs_two_prizes(second, third)
        first_second_third_keys, first_second_third_routes = set(), []
        first_second_third_positions = []
        for left, right in combinations(range(4), 2):
            position = f"{left + 1}+{right + 1}"
            duo = first[left] + first[right]
            for suffix in second_third_suffixes:
                generated = f"{duo}{suffix}"
                generated_key = unordered_digit_key4(generated)
                first_second_third_keys.add(generated_key)
                for target_number, target_key in zip(actual_nums, actual_digit_keys):
                    if generated_key != target_key:
                        continue
                    first_second_third_positions.append(position)
                    first_second_third_routes.append(
                        f"{position} | {duo}+{suffix}={generated} -> {target_number}"
                    )
        first_second_third_hits = list(dict.fromkeys(
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in first_second_third_keys
        ))
        first_second_third_bridge_hits = list(dict.fromkeys(
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in first_second_third_keys and target_key in v2_digit_keys
        ))

        # Engine berasingan: 2D daripada 2nd + missing + satu digit 1st.
        # Semua 6 kedudukan 2D dan semua 4 kedudukan digit 1st diuji.
        carry_routes = []
        carry_candidate_keys = set()
        carry_hit_numbers = []
        carry_hit_second_positions = []
        carry_hit_first_positions = []
        for left, right in combinations(range(4), 2):
            second_position = f"{left + 1}+{right + 1}"
            duo = second[left] + second[right]
            for first_position in range(4):
                first_digit = first[first_position]
                for missing_digit in carry_missing:
                    generated = f"{duo}{missing_digit}{first_digit}"
                    generated_key = unordered_digit_key4(generated)
                    carry_candidate_keys.add(generated_key)
                    for target_number, target_key in zip(actual_nums, actual_digit_keys):
                        if generated_key != target_key:
                            continue
                        carry_hit_numbers.append(target_number)
                        carry_hit_second_positions.append(second_position)
                        carry_hit_first_positions.append(str(first_position + 1))
                        carry_routes.append(
                            f"{second_position} x 1st-{first_position + 1} | "
                            f"{duo}+{missing_digit}+{first_digit} | "
                            f"{generated} -> {target_number}"
                        )
        carry_hit_numbers = list(dict.fromkeys(carry_hit_numbers))
        carry_hit_second_positions = list(dict.fromkeys(carry_hit_second_positions))
        carry_hit_first_positions = list(dict.fromkeys(carry_hit_first_positions))
        carry_routes = list(dict.fromkeys(carry_routes))

        # Engine berasingan: 2D daripada 2nd + dua digit 1st/3rd mengikut
        # kemunculan sebenar. Double dibenarkan hanya jika benar-benar muncul.
        first_third_pool = first + third
        first_third_suffixes = sorted({
            "".join(sorted((first_third_pool[left], first_third_pool[right])))
            for left, right in combinations(range(len(first_third_pool)), 2)
        })
        ft_candidate_keys = set()
        ft_hit_numbers, ft_hit_positions, ft_hit_duos, ft_hit_routes = [], [], [], []
        for left, right in combinations(range(4), 2):
            ft_position = f"{left + 1}+{right + 1}"
            ft_duo = second[left] + second[right]
            for ft_suffix in first_third_suffixes:
                ft_generated = f"{ft_duo}{ft_suffix}"
                ft_key = unordered_digit_key4(ft_generated)
                ft_candidate_keys.add(ft_key)
                for target_number, target_key in zip(actual_nums, actual_digit_keys):
                    if ft_key != target_key:
                        continue
                    ft_hit_numbers.append(target_number)
                    ft_hit_positions.append(ft_position)
                    ft_hit_duos.append(ft_duo)
                    ft_hit_routes.append(
                        f"{ft_position} | {ft_duo}+{ft_suffix}="
                        f"{ft_generated} -> {target_number}"
                    )
        ft_hit_numbers = list(dict.fromkeys(ft_hit_numbers))
        ft_hit_positions = list(dict.fromkeys(ft_hit_positions))
        ft_hit_duos = list(dict.fromkeys(ft_hit_duos))
        ft_hit_routes = list(dict.fromkeys(ft_hit_routes))

        # Enjin berasingan: 2D daripada 3rd + missing + satu digit 1st.
        third_missing_keys, third_missing_routes = set(), []
        third_missing_positions, third_missing_first_positions = [], []
        for left, right in combinations(range(4), 2):
            position = f"{left + 1}+{right + 1}"
            duo = third[left] + third[right]
            for first_position, first_digit in enumerate(first, start=1):
                for missing_digit in carry_missing:
                    generated = f"{duo}{missing_digit}{first_digit}"
                    generated_key = unordered_digit_key4(generated)
                    third_missing_keys.add(generated_key)
                    for target_number, target_key in zip(actual_nums, actual_digit_keys):
                        if generated_key != target_key:
                            continue
                        third_missing_positions.append(position)
                        third_missing_first_positions.append(str(first_position))
                        third_missing_routes.append(
                            f"{position} x 1st-{first_position} | "
                            f"{duo}+{missing_digit}+{first_digit} | "
                            f"{generated} -> {target_number}"
                        )
        third_missing_hits = [
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in third_missing_keys
        ]
        third_missing_bridge_hits = [
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in third_missing_keys and target_key in v1_digit_keys
        ]
        third_missing_hits = list(dict.fromkeys(third_missing_hits))
        third_missing_bridge_hits = list(dict.fromkeys(third_missing_bridge_hits))
        third_missing_positions = list(dict.fromkeys(third_missing_positions))
        third_missing_first_positions = list(dict.fromkeys(third_missing_first_positions))
        third_missing_routes = list(dict.fromkeys(third_missing_routes))

        # Enjin berasingan: 2D daripada 3rd + dua digit 1st/2nd.
        first_second_suffixes = _occurrence_pairs_two_prizes(first, second)
        third_first_second_keys, third_first_second_routes = set(), []
        third_first_second_positions, third_first_second_duos = [], []
        for left, right in combinations(range(4), 2):
            position = f"{left + 1}+{right + 1}"
            duo = third[left] + third[right]
            for suffix in first_second_suffixes:
                generated = f"{duo}{suffix}"
                generated_key = unordered_digit_key4(generated)
                third_first_second_keys.add(generated_key)
                for target_number, target_key in zip(actual_nums, actual_digit_keys):
                    if generated_key != target_key:
                        continue
                    third_first_second_positions.append(position)
                    third_first_second_duos.append(duo)
                    third_first_second_routes.append(
                        f"{position} | {duo}+{suffix}={generated} -> {target_number}"
                    )
        third_first_second_hits = [
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in third_first_second_keys
        ]
        third_first_second_bridge_hits = [
            number for number, target_key in zip(actual_nums, actual_digit_keys)
            if target_key in third_first_second_keys and target_key in v2_digit_keys
        ]
        third_first_second_hits = list(dict.fromkeys(third_first_second_hits))
        third_first_second_bridge_hits = list(dict.fromkeys(third_first_second_bridge_hits))
        third_first_second_positions = list(dict.fromkeys(third_first_second_positions))
        third_first_second_duos = list(dict.fromkeys(third_first_second_duos))
        third_first_second_routes = list(dict.fromkeys(third_first_second_routes))

        # Bridge Solo: pemenang Bridge yang tidak mendapat sokongan daripada
        # mana-mana tiga engine sepadan. Ini aras berasingan, bukan Double Match.
        v1_engine_hit_keys = (
            {unordered_digit_key4(x) for values in first_missing_bridge_hits.values() for x in values}
            | {unordered_digit_key4(x) for x in carry_hit_numbers}
            | {unordered_digit_key4(x) for x in third_missing_bridge_hits}
        )
        v2_engine_hit_keys = (
            {unordered_digit_key4(x) for x in first_second_third_bridge_hits}
            | {unordered_digit_key4(x) for x in ft_hit_numbers}
            | {unordered_digit_key4(x) for x in third_first_second_bridge_hits}
        )
        bridge_solo_v1_hits = [
            number for number in v1_hits
            if unordered_digit_key4(number) not in v1_engine_hit_keys
        ]
        bridge_solo_v2_hits = [
            number for number in v2_hits
            if unordered_digit_key4(number) not in v2_engine_hit_keys
        ]

        def hit_state(values):
            return "PENDING" if status == "PENDING" else ("YES" if values else "NO")
        row = {
            "Source Draw": str(source.get("draw_no", idx)),
            "Source Result": f"{first} / {second} / {third}",
            "Next Draw": next_draw, "Next Result": next_result,
            "Bridge Count": len(v1_list), "Bridge List": " / ".join(v1_list),
            "Bridge Hit": hit_state(v1_hits), "Bridge Hit Number": " / ".join(v1_hits),
            "Bridge V2 Count": len(v2_list), "Bridge V2 List": " / ".join(v2_list),
            "Bridge V2 Hit": hit_state(v2_hits), "Bridge V2 Hit Number": " / ".join(v2_hits),
            "Bridge V2 2-Missing Hit": hit_state(missing_hits),
            "Bridge V2 2-Missing Hit Number": " / ".join(missing_hits),
            "Bridge V2 2-Existing Hit": hit_state(existing_hits),
            "Bridge V2 2-Existing Hit Number": " / ".join(existing_hits),
            "Hit": hit_state(union_hits), "Hit Number": " / ".join(union_hits),
            "Bridge Solo V1 Hit": hit_state(bridge_solo_v1_hits),
            "Bridge Solo V1 Hit Number": " / ".join(bridge_solo_v1_hits),
            "Bridge Solo V2 Hit": hit_state(bridge_solo_v2_hits),
            "Bridge Solo V2 Hit Number": " / ".join(bridge_solo_v2_hits),
            "1st2D+Missing2nd Candidate Count": len(first_missing_keys["Digit 2nd"]),
            "1st2D+Missing2nd Hit": hit_state(first_missing_hits["Digit 2nd"]),
            "1st2D+Missing2nd Hit Number": " / ".join(first_missing_hits["Digit 2nd"]),
            "1st2D+Missing2nd Bridge Hit": hit_state(first_missing_bridge_hits["Digit 2nd"]),
            "1st2D+Missing2nd Bridge Hit Number": " / ".join(first_missing_bridge_hits["Digit 2nd"]),
            "1st2D+Missing2nd Hit Positions": " / ".join(dict.fromkeys(first_missing_positions["Digit 2nd"])),
            "1st2D+Missing2nd Hit Routes": " || ".join(dict.fromkeys(first_missing_routes["Digit 2nd"])),
            "1st2D+Missing3rd Candidate Count": len(first_missing_keys["Digit 3rd"]),
            "1st2D+Missing3rd Hit": hit_state(first_missing_hits["Digit 3rd"]),
            "1st2D+Missing3rd Hit Number": " / ".join(first_missing_hits["Digit 3rd"]),
            "1st2D+Missing3rd Bridge Hit": hit_state(first_missing_bridge_hits["Digit 3rd"]),
            "1st2D+Missing3rd Bridge Hit Number": " / ".join(first_missing_bridge_hits["Digit 3rd"]),
            "1st2D+Missing3rd Hit Positions": " / ".join(dict.fromkeys(first_missing_positions["Digit 3rd"])),
            "1st2D+Missing3rd Hit Routes": " || ".join(dict.fromkeys(first_missing_routes["Digit 3rd"])),
            "1st2D+2nd3rd Candidate Count": len(first_second_third_keys),
            "1st2D+2nd3rd Hit": hit_state(first_second_third_hits),
            "1st2D+2nd3rd Hit Number": " / ".join(first_second_third_hits),
            "1st2D+2nd3rd Bridge Hit": hit_state(first_second_third_bridge_hits),
            "1st2D+2nd3rd Bridge Hit Number": " / ".join(first_second_third_bridge_hits),
            "1st2D+2nd3rd Hit Positions": " / ".join(dict.fromkeys(first_second_third_positions)),
            "1st2D+2nd3rd Hit Routes": " || ".join(dict.fromkeys(first_second_third_routes)),
            "2D+Missing Candidate Count": len(carry_candidate_keys),
            "2D+Missing Hit": hit_state(carry_hit_numbers),
            "2D+Missing Hit Number": " / ".join(carry_hit_numbers),
            "2D+Missing Hit 2D Positions": " / ".join(carry_hit_second_positions),
            "2D+Missing Hit 1st Positions": " / ".join(carry_hit_first_positions),
            "2D+Missing Hit Routes": " || ".join(carry_routes),
            "2D+1st3rd Candidate Count": len(ft_candidate_keys),
            "2D+1st3rd Hit": hit_state(ft_hit_numbers),
            "2D+1st3rd Hit Number": " / ".join(ft_hit_numbers),
            "2D+1st3rd Hit Positions": " / ".join(ft_hit_positions),
            "2D+1st3rd Hit 2D": " / ".join(ft_hit_duos),
            "2D+1st3rd Hit Routes": " || ".join(ft_hit_routes),
            "3rd2D+Missing Candidate Count": len(third_missing_keys),
            "3rd2D+Missing Hit": hit_state(third_missing_hits),
            "3rd2D+Missing Hit Number": " / ".join(third_missing_hits),
            "3rd2D+Missing Bridge Hit": hit_state(third_missing_bridge_hits),
            "3rd2D+Missing Bridge Hit Number": " / ".join(third_missing_bridge_hits),
            "3rd2D+Missing Hit Positions": " / ".join(third_missing_positions),
            "3rd2D+Missing Hit 1st Positions": " / ".join(third_missing_first_positions),
            "3rd2D+Missing Hit Routes": " || ".join(third_missing_routes),
            "3rd2D+1st2nd Candidate Count": len(third_first_second_keys),
            "3rd2D+1st2nd Hit": hit_state(third_first_second_hits),
            "3rd2D+1st2nd Hit Number": " / ".join(third_first_second_hits),
            "3rd2D+1st2nd Bridge Hit": hit_state(third_first_second_bridge_hits),
            "3rd2D+1st2nd Bridge Hit Number": " / ".join(third_first_second_bridge_hits),
            "3rd2D+1st2nd Hit Positions": " / ".join(third_first_second_positions),
            "3rd2D+1st2nd Hit 2D": " / ".join(third_first_second_duos),
            "3rd2D+1st2nd Hit Routes": " || ".join(third_first_second_routes),
        }
        rows.append(row)
        cache[key] = row
    try:
        cache_path.write_text(json.dumps({"version": "v31.55-bridge-solo", "rows": cache}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    detail = pd.DataFrame(rows)
    valid = detail[detail.get("Hit", pd.Series(dtype=str)).astype(str).isin(["YES", "NO"])]
    total = len(valid)
    v1_yes = int(valid.get("Bridge Hit", pd.Series(dtype=str)).eq("YES").sum())
    v2_yes = int(valid.get("Bridge V2 Hit", pd.Series(dtype=str)).eq("YES").sum())
    union_yes = int(valid.get("Hit", pd.Series(dtype=str)).eq("YES").sum())
    miss_yes = int(valid.get("Bridge V2 2-Missing Hit", pd.Series(dtype=str)).eq("YES").sum())
    exist_yes = int(valid.get("Bridge V2 2-Existing Hit", pd.Series(dtype=str)).eq("YES").sum())
    summary = pd.DataFrame([
        {"Metric": "Tested source draws", "Value": total},
        {"Metric": "Pending latest draw", "Value": int(detail.get("Hit", pd.Series(dtype=str)).eq("PENDING").sum())},
        {"Metric": "Bridge V1 YES", "Value": v1_yes},
        {"Metric": "Bridge V1 Hit Rate %", "Value": round(v1_yes / total * 100, 1) if total else 0},
        {"Metric": "Bridge V2 YES", "Value": v2_yes},
        {"Metric": "Bridge V2 Hit Rate %", "Value": round(v2_yes / total * 100, 1) if total else 0},
        {"Metric": "V2 2-Missing YES", "Value": miss_yes},
        {"Metric": "V2 2-Existing YES", "Value": exist_yes},
        {"Metric": "Bridge V1 atau V2 Hit", "Value": union_yes},
        {"Metric": "Total Unique Hit Rate %", "Value": round(union_yes / total * 100, 1) if total else 0},
        {"Metric": "Elapsed Seconds", "Value": round(time.perf_counter() - t0, 3)},
    ])
    return summary, detail

def _first_existing_backtest_column(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def build_clean_backtest_quick_review(detail_df):
    """Paparan ringkas dalam urutan tetap: Bridge, Solo, 1st, 2nd, 3rd."""
    values = {}
    for target, choices in {
        "Source Draw": ["Source Draw"],
        "Source Result": ["Source Result"],
        "Next Draw": ["Next Draw"],
        "Next Result": ["Next Result"],
        "Bridge Hit No": ["Bridge Hit Number", "Bridge Hit No"],
        "Bridge V2 Hit No": ["Bridge V2 Hit Number", "Bridge V2 Hit No"],
        "Solo V1 Hit No": ["Bridge Solo V1 Hit Number"],
        "Solo V2 Hit No": ["Bridge Solo V2 Hit Number"],
        "1st 2nd+3rd Hit No": ["1st2D+2nd3rd Bridge Hit Number"],
        "2nd Missing Hit No": ["2D+Missing Hit Number"],
        "2nd 1st+3rd Hit No": ["2D+1st3rd Hit Number"],
        "3rd Missing Hit No": ["3rd2D+Missing Bridge Hit Number"],
        "3rd 1st+2nd Hit No": ["3rd2D+1st2nd Bridge Hit Number"],
    }.items():
        source = _first_existing_backtest_column(detail_df, choices)
        values[target] = (
            detail_df[source].fillna("").astype(str)
            if source else pd.Series("", index=detail_df.index)
        )
    first_missing_columns = [
        column for column in (
            "1st2D+Missing2nd Bridge Hit Number",
            "1st2D+Missing3rd Bridge Hit Number",
        ) if column in detail_df.columns
    ]
    if first_missing_columns:
        first_missing = detail_df[first_missing_columns].apply(
            lambda row: " / ".join(dict.fromkeys(
                number.strip()
                for value in row.fillna("").astype(str)
                for number in value.split("/")
                if number.strip()
            )), axis=1,
        )
    else:
        first_missing = pd.Series("", index=detail_df.index)
    values["1st Missing Hit No"] = first_missing
    ordered_columns = [
        "Source Draw", "Source Result", "Next Draw", "Next Result",
        "Bridge Hit No", "Bridge V2 Hit No",
        "Solo V1 Hit No", "Solo V2 Hit No",
        "1st Missing Hit No", "1st 2nd+3rd Hit No",
        "2nd Missing Hit No", "2nd 1st+3rd Hit No",
        "3rd Missing Hit No", "3rd 1st+2nd Hit No",
    ]
    q = pd.DataFrame(
        {column: values[column] for column in ordered_columns},
        index=detail_df.index,
    )
    return q.reset_index(drop=True)


def build_clean_backtest_summary(detail_df):
    """Summary mesra pengguna untuk Bridge V1 dan V2."""
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
    def hit_from_numbers(*columns):
        existing = [column for column in columns if column in valid.columns]
        if not existing:
            return 0
        return int(valid[existing].fillna("").astype(str).apply(
            lambda row: any(value.strip() for value in row), axis=1
        ).sum())

    def append_engine(name, hits):
        rows.extend([
            {"Metric": f"{name} Hit", "Value": int(hits)},
            {"Metric": f"{name} Hit Rate %", "Value": round(hits / completed * 100, 1) if completed else 0},
        ])

    append_engine("Solo V1", hit_from_numbers("Bridge Solo V1 Hit Number"))
    append_engine("Solo V2", hit_from_numbers("Bridge Solo V2 Hit Number"))
    append_engine("1st Missing", hit_from_numbers(
        "1st2D+Missing2nd Bridge Hit Number", "1st2D+Missing3rd Bridge Hit Number"
    ))
    append_engine("1st 2nd+3rd", hit_from_numbers("1st2D+2nd3rd Bridge Hit Number"))
    append_engine("2nd Missing", hit_from_numbers("2D+Missing Hit Number"))
    append_engine("2nd 1st+3rd", hit_from_numbers("2D+1st3rd Hit Number"))
    append_engine("3rd Missing", hit_from_numbers("3rd2D+Missing Bridge Hit Number"))
    append_engine("3rd 1st+2nd", hit_from_numbers("3rd2D+1st2nd Bridge Hit Number"))
    summary = pd.DataFrame(rows)
    summary["Value"] = summary["Value"].astype(str)
    return summary


def build_2d_missing_backtest_summary(detail_df):
    """Ringkasan engine 2D + missing tanpa dicampur dengan Bridge."""
    status = detail_df.get(
        "2D+Missing Hit", pd.Series("", index=detail_df.index)
    ).astype(str)
    valid = detail_df.loc[status.isin(["YES", "NO"])].copy()
    completed = len(valid)
    total_hits = int(valid.get(
        "2D+Missing Hit", pd.Series("", index=valid.index)
    ).astype(str).eq("YES").sum())
    rows = [
        {"Kategori": "Keseluruhan", "Laluan": "Mana-mana laluan", "Hit Draw": total_hits,
         "Draw Diuji": completed,
         "Hit Rate %": round(total_hits / completed * 100, 1) if completed else 0},
    ]

    def count_token(column, token):
        if column not in valid.columns:
            return 0
        return int(valid[column].fillna("").astype(str).apply(
            lambda value: token in [part.strip() for part in value.split("/")]
        ).sum())

    for left, right in combinations(range(4), 2):
        label = f"{left + 1}+{right + 1}"
        hits = count_token("2D+Missing Hit 2D Positions", label)
        rows.append({
            "Kategori": "Kedudukan 2D", "Laluan": label,
            "Hit Draw": hits, "Draw Diuji": completed,
            "Hit Rate %": round(hits / completed * 100, 1) if completed else 0,
        })
    for position in range(1, 5):
        hits = count_token("2D+Missing Hit 1st Positions", str(position))
        rows.append({
            "Kategori": "Kedudukan Digit 1st", "Laluan": str(position),
            "Hit Draw": hits, "Draw Diuji": completed,
            "Hit Rate %": round(hits / completed * 100, 1) if completed else 0,
        })
    return pd.DataFrame(rows)


def build_2d_missing_backtest_detail(detail_df):
    columns = [
        "Source Draw", "Source Result", "Next Draw", "Next Result",
        "2D+Missing Candidate Count", "2D+Missing Hit",
        "2D+Missing Hit Number", "2D+Missing Hit 2D Positions",
        "2D+Missing Hit 1st Positions", "2D+Missing Hit Routes",
    ]
    return detail_df.reindex(columns=columns).copy()


def build_first_third_backtest_summary(detail_df):
    """Ringkasan 2D 2nd + dua digit 1st/3rd secara berasingan."""
    status = detail_df.get(
        "2D+1st3rd Hit", pd.Series("", index=detail_df.index)
    ).astype(str)
    valid = detail_df.loc[status.isin(["YES", "NO"])].copy()
    completed = len(valid)
    total_hits = int(valid.get(
        "2D+1st3rd Hit", pd.Series("", index=valid.index)
    ).astype(str).eq("YES").sum())
    rows = [{
        "Kategori": "Keseluruhan", "Laluan": "Mana-mana laluan",
        "Hit Draw": total_hits, "Draw Diuji": completed,
        "Hit Rate %": round(total_hits / completed * 100, 1) if completed else 0,
    }]
    for left, right in combinations(range(4), 2):
        label = f"{left + 1}+{right + 1}"
        hits = int(valid.get(
            "2D+1st3rd Hit Positions", pd.Series("", index=valid.index)
        ).fillna("").astype(str).apply(
            lambda value: label in [part.strip() for part in value.split("/")]
        ).sum())
        rows.append({
            "Kategori": "Kedudukan 2D", "Laluan": label,
            "Hit Draw": hits, "Draw Diuji": completed,
            "Hit Rate %": round(hits / completed * 100, 1) if completed else 0,
        })
    return pd.DataFrame(rows)


def build_first_third_backtest_detail(detail_df):
    columns = [
        "Source Draw", "Source Result", "Next Draw", "Next Result",
        "2D+1st3rd Candidate Count", "2D+1st3rd Hit",
        "2D+1st3rd Hit Number", "2D+1st3rd Hit Positions",
        "2D+1st3rd Hit 2D", "2D+1st3rd Hit Routes",
    ]
    return detail_df.reindex(columns=columns).copy()


def build_third_route_backtest_summary(detail_df, prefix, label):
    """Ringkasan satu laluan 1st/3rd; tidak digabung dengan laluan lain."""
    status_column = f"{prefix} Hit"
    bridge_column = f"{prefix} Bridge Hit"
    status = detail_df.get(status_column, pd.Series("", index=detail_df.index)).astype(str)
    valid = detail_df.loc[status.isin(["YES", "NO"])].copy()
    completed = len(valid)
    raw_hits = int(valid.get(
        status_column, pd.Series("", index=valid.index)
    ).astype(str).eq("YES").sum())
    bridge_hits = int(valid.get(
        bridge_column, pd.Series("", index=valid.index)
    ).astype(str).eq("YES").sum())
    rows = [
        {"Kategori": "Keseluruhan", "Laluan": label,
         "Hit Draw": raw_hits, "Draw Diuji": completed,
         "Hit Rate %": round(raw_hits / completed * 100, 1) if completed else 0},
        {"Kategori": "Selepas Bridge", "Laluan": label,
         "Hit Draw": bridge_hits, "Draw Diuji": completed,
         "Hit Rate %": round(bridge_hits / completed * 100, 1) if completed else 0},
    ]
    position_column = f"{prefix} Hit Positions"
    prize_name = "1st" if str(prefix).startswith("1st") else "3rd"
    for left, right in combinations(range(4), 2):
        position = f"{left + 1}+{right + 1}"
        hits = int(valid.get(
            position_column, pd.Series("", index=valid.index)
        ).fillna("").astype(str).apply(
            lambda value: position in [part.strip() for part in value.split("/")]
        ).sum())
        rows.append({
            "Kategori": f"Kedudukan {prize_name} 2D", "Laluan": position,
            "Hit Draw": hits, "Draw Diuji": completed,
            "Hit Rate %": round(hits / completed * 100, 1) if completed else 0,
        })
    return pd.DataFrame(rows)


def build_third_route_backtest_detail(detail_df, prefix):
    columns = [
        "Source Draw", "Source Result", "Next Draw", "Next Result",
        f"{prefix} Candidate Count", f"{prefix} Hit", f"{prefix} Hit Number",
        f"{prefix} Bridge Hit", f"{prefix} Bridge Hit Number",
        f"{prefix} Hit Positions", f"{prefix} Hit Routes",
    ]
    return detail_df.reindex(columns=columns).copy()


def build_first_missing_backtest_summary(detail_df):
    """Satu summary untuk laluan Missing 1st; sumber digit kekal boleh diaudit."""
    frames = []
    for prefix, source in (
        ("1st2D+Missing2nd", "Digit 2nd"),
        ("1st2D+Missing3rd", "Digit 3rd"),
    ):
        frame = build_third_route_backtest_summary(
            detail_df, prefix, f"1st 2D + Missing + {source}"
        )
        frame.insert(1, "Sumber Digit", source)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_first_missing_backtest_detail(detail_df):
    """Satu detail untuk kedua-dua sumber digit laluan Missing 1st."""
    frames = []
    for prefix, source in (
        ("1st2D+Missing2nd", "Digit 2nd"),
        ("1st2D+Missing3rd", "Digit 3rd"),
    ):
        frame = build_third_route_backtest_detail(detail_df, prefix)
        frame = frame.rename(columns={
            column: column.replace(prefix, "1st2D+Missing")
            for column in frame.columns if prefix in column
        })
        frame.insert(4, "Sumber Digit", source)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def simple_backtest_excel_bytes(summary_df, detail_df):
    from io import BytesIO
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    quick_df = build_clean_backtest_quick_review(detail_df)
    clean_summary_df = build_clean_backtest_summary(detail_df)
    first_missing_summary_df = build_first_missing_backtest_summary(detail_df)
    first_missing_detail_df = build_first_missing_backtest_detail(detail_df)
    first_second_third_summary_df = build_third_route_backtest_summary(
        detail_df, "1st2D+2nd3rd", "1st 2D + Digit 2nd & 3rd"
    )
    first_second_third_detail_df = build_third_route_backtest_detail(
        detail_df, "1st2D+2nd3rd"
    )
    carry_summary_df = build_2d_missing_backtest_summary(detail_df)
    carry_detail_df = build_2d_missing_backtest_detail(detail_df)
    first_third_summary_df = build_first_third_backtest_summary(detail_df)
    first_third_detail_df = build_first_third_backtest_detail(detail_df)
    third_missing_summary_df = build_third_route_backtest_summary(
        detail_df, "3rd2D+Missing", "3rd 2D + Missing + Digit 1st"
    )
    third_missing_detail_df = build_third_route_backtest_detail(
        detail_df, "3rd2D+Missing"
    )
    third_first_second_summary_df = build_third_route_backtest_summary(
        detail_df, "3rd2D+1st2nd", "3rd 2D + Digit 1st & 2nd"
    )
    third_first_second_detail_df = build_third_route_backtest_detail(
        detail_df, "3rd2D+1st2nd"
    )

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
        first_missing_summary_df.to_excel(
            writer, sheet_name="1st Missing Summary", index=False
        )
        first_missing_detail_df.to_excel(
            writer, sheet_name="1st Missing Detail", index=False
        )
        first_second_third_summary_df.to_excel(
            writer, sheet_name="1st 2nd3rd Summary", index=False
        )
        first_second_third_detail_df.to_excel(
            writer, sheet_name="1st 2nd3rd Detail", index=False
        )
        carry_summary_df.to_excel(writer, sheet_name="2nd Missing Summary", index=False)
        carry_detail_df.to_excel(writer, sheet_name="2nd Missing Detail", index=False)
        first_third_summary_df.to_excel(writer, sheet_name="2nd 1st3rd Summary", index=False)
        first_third_detail_df.to_excel(writer, sheet_name="2nd 1st3rd Detail", index=False)
        third_missing_summary_df.to_excel(writer, sheet_name="3rd Missing Summary", index=False)
        third_missing_detail_df.to_excel(writer, sheet_name="3rd Missing Detail", index=False)
        third_first_second_summary_df.to_excel(writer, sheet_name="3rd 1st2nd Summary", index=False)
        third_first_second_detail_df.to_excel(writer, sheet_name="3rd 1st2nd Detail", index=False)

        wb = writer.book
        navy = "17365D"
        pale_green = "EAF7EE"
        pale_solo = "E8F7F4"
        pale_blue = "EEF4FF"
        pale_gold = "FFF4D6"
        light_border = Side(style="thin", color="E5E7EB")

        quick_ws = wb["Quick Review"]
        quick_ws.freeze_panes = "A2"
        quick_ws.sheet_view.showGridLines = False
        quick_ws.sheet_view.zoomScale = 65
        quick_ws.auto_filter.ref = quick_ws.dimensions
        for cell in quick_ws[1]:
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
        quick_ws.row_dimensions[1].height = 42
        quick_headers = {
            str(cell.value): cell.column
            for cell in quick_ws[1] if cell.value is not None
        }
        quick_groups = {
            "bridge": ["Bridge Hit No", "Bridge V2 Hit No"],
            "solo": ["Solo V1 Hit No", "Solo V2 Hit No"],
            "first": ["1st Missing Hit No", "1st 2nd+3rd Hit No"],
            "second": ["2nd Missing Hit No", "2nd 1st+3rd Hit No"],
            "third": ["3rd Missing Hit No", "3rd 1st+2nd Hit No"],
        }
        for row in quick_ws.iter_rows(min_row=2, max_row=quick_ws.max_row):
            for cell in row:
                cell.border = Border(bottom=light_border)
                cell.alignment = Alignment(vertical="center")
                cell.number_format = "@"
            # Bridge V1/V2
            for name in quick_groups["bridge"]:
                cell = row[quick_headers[name] - 1]
                cell.fill = PatternFill("solid", fgColor=pale_green)
                cell.font = Font(color="166534", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # Bridge Solo ialah kumpulan tersendiri, bukan laluan 1st.
            for name in quick_groups["solo"]:
                cell = row[quick_headers[name] - 1]
                cell.fill = PatternFill("solid", fgColor=pale_solo)
                cell.font = Font(color="0F766E", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # Dua laluan berasaskan 1st Prize
            for name in quick_groups["first"]:
                cell = row[quick_headers[name] - 1]
                cell.fill = PatternFill("solid", fgColor="F3E8FF")
                cell.font = Font(color="6B21A8", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # Dua laluan berasaskan 2nd Prize
            for name in quick_groups["second"]:
                cell = row[quick_headers[name] - 1]
                cell.fill = PatternFill("solid", fgColor=pale_blue)
                cell.font = Font(color="1E3A8A", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # Dua laluan berasaskan 3rd Prize
            for name in quick_groups["third"]:
                cell = row[quick_headers[name] - 1]
                cell.fill = PatternFill("solid", fgColor=pale_gold)
                cell.font = Font(color="92400E", bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")
        for col, width in {
            "A": 10, "B": 20, "C": 10, "D": 20,
            "E": 13, "F": 13, "G": 15, "H": 15,
            "I": 15, "J": 15, "K": 15, "L": 15,
            "M": 15, "N": 15,
        }.items():
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
        detail_ws.sheet_view.showGridLines = False
        detail_ws.sheet_view.zoomScale = 60
        detail_ws.auto_filter.ref = detail_ws.dimensions
        for cell in detail_ws[1]:
            cell.fill = PatternFill("solid", fgColor=navy)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
        detail_ws.row_dimensions[1].height = 44
        for column_cells in detail_ws.columns:
            letter = column_cells[0].column_letter
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            detail_ws.column_dimensions[letter].width = min(max(max_length + 2, 10), 24)

        for sheet_name in (
            "1st Missing Summary", "1st Missing Detail",
            "1st 2nd3rd Summary", "1st 2nd3rd Detail",
            "2nd Missing Summary", "2nd Missing Detail",
            "2nd 1st3rd Summary", "2nd 1st3rd Detail",
            "3rd Missing Summary", "3rd Missing Detail",
            "3rd 1st2nd Summary", "3rd 1st2nd Detail",
        ):
            ws = wb[sheet_name]
            ws.freeze_panes = "A2"
            ws.sheet_view.showGridLines = False
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.fill = PatternFill("solid", fgColor=navy)
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(
                    horizontal="center", vertical="center", wrap_text=True
                )
            ws.row_dimensions[1].height = 38
            ws.sheet_view.zoomScale = 75
            for column_cells in ws.columns:
                letter = column_cells[0].column_letter
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                ws.column_dimensions[letter].width = min(max(max_length + 2, 10), 28)

    output.seek(0)
    return output.getvalue()

# -----------------------------
# V31.6: Simple Backtest
# -----------------------------
with tools_tabs[1]:


    @st.cache_data(show_spinner=False)
    def _cached_walk_forward(history_df, test_draws, k, window):
        return run_walk_forward(prepare_draws(history_df), test_draws=test_draws, k=k, window=window)


    st.markdown("#### 🎲 Backtest vs Rawak (Top-K, walk-forward)")
    with st.container():
        st.caption(
            "Setiap strategi hanya nampak draw SEBELUM draw yang diuji, pilih K nombor, "
            "kemudian dibandingkan dengan peluang rawak. Gunakan lajur 'p terlaras' untuk kesimpulan."
        )
        wf_col1, wf_col2, wf_col3 = st.columns(3)
        with wf_col1:
            wf_draws = st.selectbox("Jumlah draw diuji", [500, 1000, 2000, 3000], index=2, key="wf_bt_draws")
        with wf_col2:
            wf_k = st.selectbox("Bilangan nombor dipilih (K)", [5, 10, 20, 50], index=1, key="wf_bt_k")
        with wf_col3:
            wf_window = st.selectbox("Tetingkap terkini", [100, 300, 500, 1000], index=1, key="wf_bt_window")

        if st.button("Run Backtest vs Rawak", key="run_wf_bt"):
            with st.spinner("Backtest walk-forward sedang berjalan..."):
                wf_table = _cached_walk_forward(st.session_state.history, wf_draws, wf_k, wf_window)
            st.dataframe(wf_table, hide_index=True, use_container_width=True)
            st.info(baseline_verdict(wf_table))
            st.caption(
                "Exact = nombor tepat sama. Box = digit disusun semula dikira sama. "
                "Cabutan 4D ialah rawak; keputusan yang 'hampir signifikan' tanpa p terlaras "
                "biasanya muncul kerana banyak strategi diuji serentak."
            )
            st.download_button(
                "Muat turun keputusan (CSV)",
                wf_table.to_csv(index=False).encode("utf-8"),
                file_name=f"Rumah_A_Backtest_vs_Rawak_Top{wf_k}_{wf_draws}draw.csv",
                mime="text/csv",
                key="dl_wf_bt",
            )

    @st.cache_data(show_spinner=False)
    def _cached_pair_diag(history_df, test_draws):
        return pair_ranking_diagnostics(history_df, test_draws=test_draws)


    st.divider()
    st.markdown("#### 📈 Diagnostik Ranking Pair (berubah? meramal?)")
    with st.container():
        st.caption(
            "Menguji ranking pair secara walk-forward: (1) adakah pair teratas berubah mengikut draw, "
            "(2) adakah ranking teratas benar-benar hit lebih kerap daripada peluang rawak."
        )
        diag_draws = st.selectbox("Jumlah draw diuji", [200, 500, 1000], index=1, key="pair_diag_draws")
        if st.button("Run Diagnostik Ranking", key="run_pair_diag"):
            with st.spinner("Diagnostik sedang berjalan..."):
                diag = _cached_pair_diag(st.session_state.history[["first", "second", "third"]], diag_draws)
            st.markdown("**Kepelbagaian ranking teratas**")
            st.dataframe(diag["diversity"], hide_index=True, use_container_width=True)
            st.markdown("**Hit mengikut ranking vs jangkaan rawak**")
            st.dataframe(diag["by_rank"], hide_index=True, use_container_width=True)
            st.caption(
                "Jika 'Hit %' ranking 1 tidak jauh lebih tinggi daripada ranking terakhir dan "
                "'p terlaras' besar, susunan itu tidak meramal; ia hanya berubah mengikut draw."
            )
            with st.expander("Slot yang pernah di ranking 1", expanded=False):
                st.dataframe(diag["top_slot_counts"], use_container_width=True)


    st.divider()
    st.markdown("#### 🧪 Backtest Bridge V1 + V2")
    with st.container():
        st.caption("Fast Backtest: keputusan draw lama dibaca daripada cache; hanya draw baharu atau berubah dikira semula.")
        bt_col1, bt_col2 = st.columns(2)
        with bt_col1:
            bt_draws = st.selectbox("Jumlah source draw untuk test", [10, 20, 30, 50, 100, 200, 300, 500], index=2, key="simple_bt_draws_v31_6")
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
                completed_count = max(len(bt_detail) - 1, 0)
                st.success(f"Backtest selesai: {completed_count} draw lengkap diuji.")

                # Bandingan dengan peluang rawak: hit rate box nampak tinggi kerana
                # satu calon meliputi sehingga 24 nombor, bukan kerana model meramal.
                try:
                    baseline_df = bridge_vs_chance(bt_detail)
                    if not baseline_df.empty:
                        st.markdown("**Bandingan dengan peluang rawak**")
                        st.dataframe(baseline_df, hide_index=True, use_container_width=True)
                        st.caption(
                            "Box = digit disusun semula dikira sama (liputan besar). "
                            "Jika 'Box %' hampir sama dengan 'Box rawak %', model tiada kelebihan. "
                            + baseline_verdict(baseline_df)
                        )
                except Exception as exc:
                    st.info(f"Bandingan rawak belum dapat dipaparkan: {exc}")

                with st.expander("Lihat ringkasan Bridge V1 + V2", expanded=False):
                    st.dataframe(clean_bt_summary, hide_index=True, use_container_width=True)

                with st.expander("Lihat keputusan setiap draw", expanded=False):
                    st.dataframe(bt_detail, hide_index=True, use_container_width=True)

                with st.expander("Lihat audit 1st 2D + Missing", expanded=False):
                    st.dataframe(
                        build_first_missing_backtest_summary(bt_detail),
                        hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        build_first_missing_backtest_detail(bt_detail),
                        hide_index=True, use_container_width=True,
                    )
                with st.expander("Lihat audit 1st 2D + Digit 2nd & 3rd", expanded=False):
                    st.dataframe(
                        build_third_route_backtest_summary(
                            bt_detail, "1st2D+2nd3rd",
                            "1st 2D + Digit 2nd & 3rd",
                        ), hide_index=True, use_container_width=True,
                    )

                with st.expander("Lihat audit 2nd 2D + Missing", expanded=False):
                    st.dataframe(
                        build_2d_missing_backtest_summary(bt_detail),
                        hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        build_2d_missing_backtest_detail(bt_detail),
                        hide_index=True,
                        use_container_width=True,
                    )
                with st.expander("Lihat audit 2nd 2D + Digit 1st & 3rd", expanded=False):
                    st.dataframe(
                        build_first_third_backtest_summary(bt_detail),
                        hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        build_first_third_backtest_detail(bt_detail),
                        hide_index=True,
                        use_container_width=True,
                    )
                with st.expander("Lihat audit 3rd 2D + Missing", expanded=False):
                    st.dataframe(
                        build_third_route_backtest_summary(
                            bt_detail, "3rd2D+Missing", "3rd 2D + Missing + Digit 1st"
                        ), hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        build_third_route_backtest_detail(bt_detail, "3rd2D+Missing"),
                        hide_index=True, use_container_width=True,
                    )
                with st.expander("Lihat audit 3rd 2D + Digit 1st & 2nd", expanded=False):
                    st.dataframe(
                        build_third_route_backtest_summary(
                            bt_detail, "3rd2D+1st2nd", "3rd 2D + Digit 1st & 2nd"
                        ), hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        build_third_route_backtest_detail(bt_detail, "3rd2D+1st2nd"),
                        hide_index=True, use_container_width=True,
                    )

                bt_bytes = simple_backtest_excel_bytes(bt_summary, bt_detail)
                with st.expander("Muat turun laporan Excel", expanded=False):
                    st.download_button(
                        "Download Backtest Turbo Excel",
                        data=bt_bytes,
                        file_name=backtest_filename(st.session_state.history.iloc[-1]["draw_no"], bt_draws),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_backtest_turbo_v31_7"
                    )


    def render_pair_groups(groups, key_prefix):
        """Jadual pair + satu pemilih pair + nombor yang boleh disalin (ganti expander setiap pair)."""
        if not groups:
            return
        table = pd.DataFrame([
            {"#": i, "Pair": g["Pair"], "Kedudukan": g["Kedudukan"], "Calon": len(g["Calon"])}
            for i, g in enumerate(groups, start=1)
        ])
        st.dataframe(table, hide_index=True, use_container_width=True)
        labels = [f"#{i}  Pair {g['Pair']}" for i, g in enumerate(groups, start=1)]
        pick_a, pick_b = st.columns([2, 1])
        choice = pick_a.selectbox("Pilih pair untuk lihat nombor", labels, index=0, key=f"{key_prefix}_choice")
        limit = pick_b.selectbox(
            "Had nombor", [10, 20, 30, 0], index=0,
            format_func=lambda value: "Semua" if value == 0 else f"Top {value}",
            key=f"{key_prefix}_limit",
        )
        numbers = groups[labels.index(choice)]["Calon"]
        shown = rank_pair_numbers(
            pd.DataFrame({"No": numbers, "Route": key_prefix}),
            st.session_state.history, top_n=(limit or None),
        )
        show_numbers(shown["No"].astype(str).tolist(), f"{key_prefix}_{labels.index(choice)}", highlight=3)
        st.caption(f"{len(shown)} daripada {len(numbers)} nombor, disusun ikut peluang box dan kekerapan terkini.")


    def render_bridge_pair_choices(pair_df, numbers_df, version, key_prefix, draw=None):
        """
    Pair disusun daripada skor tertinggi (ranking dinamik) dan berubah ikut draw
    terkini. Satu jadual ringkas + satu pilihan pair, bukan belasan expander.
    """
        if pair_df is None or pair_df.empty or numbers_df is None or numbers_df.empty:
            return
        ver = "V2" if "V2" in version else "V1"

        # 58/85 dan 75/57 dianggap pair yang sama; orientasi pertama dikekalkan.
        orient = {}
        for _, row in pair_df.iterrows():
            pair = str(row.get("Pair", "")).zfill(2)[-2:]
            canonical = pair_digit_key(pair)
            if pair.isdigit() and canonical not in orient:
                orient[canonical] = {
                    "Pair": pair,
                    "Sumber": f"{row.get('Source', '')} {row.get('Pair Type', '')}".strip(),
                }

        ranked = pd.DataFrame()
        if draw is not None:
            try:
                ranked = build_bridge_pair_priority(
                    st.session_state.history, draw[0], draw[1], draw[2], version=ver
                )
            except Exception:
                ranked = pd.DataFrame()

        ordered, seen = [], set()
        if not ranked.empty:
            for _, r in ranked.iterrows():
                canonical = pair_digit_key(r["Current Pair"])
                if canonical in orient and canonical not in seen:
                    seen.add(canonical)
                    item = dict(orient[canonical])
                    item.update({"Skor %": r["Skor %"], "Lift": r["Lift"]})
                    ordered.append(item)
        for canonical, item in orient.items():
            if canonical not in seen:
                ordered.append(dict(item))

        numbers_by_pair, rows = {}, []
        for rank, item in enumerate(ordered, start=1):
            pair = item["Pair"]
            selected = numbers_df[
                numbers_df["Base Pairs"].astype(str).apply(
                    lambda value: pair in [part.strip() for part in value.split("/")]
                )
            ]
            numbers = selected["No"].astype(str).str.zfill(4).tolist()
            numbers_by_pair[pair] = numbers
            rows.append({
                "#": rank, "Pair": pair, "Sumber": item["Sumber"],
                "Skor %": item.get("Skor %"), "Lift": item.get("Lift"),
                "Calon": len(numbers),
            })
        if not rows:
            return

        st.markdown(f"**Pair {version}** - disusun dari skor tertinggi. Susunan berubah mengikut draw terkini.")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        pick1, pick2 = st.columns([2, 1])
        labels = [f"#{r['#']}  Pair {r['Pair']}" for r in rows]
        choice = pick1.selectbox("Pilih pair untuk lihat nombor", labels, index=0, key=f"{key_prefix}_pair_choice")
        limit = pick2.selectbox(
            "Had nombor", [10, 20, 30, 0], index=0,
            format_func=lambda value: "Semua" if value == 0 else f"Top {value}",
            key=f"{key_prefix}_limit",
        )
        chosen_pair = rows[labels.index(choice)]["Pair"]
        all_numbers = numbers_by_pair[chosen_pair]
        shown = rank_pair_numbers(
            pd.DataFrame({"No": all_numbers, "Route": version}),
            st.session_state.history, top_n=(limit or None),
        )
        show_numbers(shown["No"].astype(str).tolist(), f"{key_prefix}_{chosen_pair}", highlight=3)
        st.caption(
            f"{len(shown)} daripada {len(all_numbers)} nombor untuk pair {chosen_pair}, "
            "disusun ikut peluang box dan kekerapan terkini."
        )


@st.cache_data(show_spinner=False)
def _latest_origin(history_df):
    """Backtest 2 draw terakhir (baris lengkap + baris pending) untuk jelaskan asal nombor terkini."""
    _summary, _detail = run_backtest_bridge_dde_lite_v31_24_5(history_df, test_draws=2)
    _latest = history_df.iloc[-1]
    return explain_latest_numbers(
        _detail,
        _latest["draw_no"],
        [pad4(_latest["first"]), pad4(_latest["second"]), pad4(_latest["third"])],
    )


with origin_box:
    try:
        _origin = _latest_origin(st.session_state.history)
    except Exception as exc:
        _origin = None
        st.caption(f"Asal nombor terkini belum dapat dipaparkan: {exc}")
    if _origin is not None:
        st.markdown(
            origin_html(
                _origin["table"].to_dict("records"),
                _origin["source_draw"], _origin["source_result"],
                origin_summary_line(_origin["table"]),
            ),
            unsafe_allow_html=True,
        )


with main_box:
    with st.form("predict_form"):
        st.markdown('<div class="rap-panel-title">Generate</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        first = c1.text_input("1st Prize", value=last["first"], max_chars=4)
        second = c2.text_input("2nd Prize", value=last["second"], max_chars=4)
        third = c3.text_input("3rd Prize", value=last["third"], max_chars=4)
        submitted = st.form_submit_button("Generate")

    if submitted:
        st.session_state["gen_inputs"] = (first, second, third)
        st.session_state["gen_inputs"] = tuple(str(v).strip().zfill(4)[-4:] for v in (first, second, third))


    if st.session_state.get("gen_inputs"):
        first, second, third = st.session_state["gen_inputs"]
        summary_box = st.container()
        tab_route, tab_match, tab_v1, tab_v2, tab_adv = st.tabs(
            ["Route", "Match", "Bridge V1", "Bridge V2", "Lanjutan"]
        )

        # -----------------------------
        # Bridge V1
        # -----------------------------
        with tab_v1:
            st.caption(
                "Pair depan/tengah/belakang + 1 missing digit + 1 existing digit. "
                "Nombor formula asal dikekalkan."
            )

            bridge_df = pd.DataFrame()
            bridge_pair_df = pd.DataFrame()
            try:
                bridge_pair_df, bridge_df, bridge_text = build_bridge_model_v31_9(first, second, third)
                if bridge_df.empty:
                    st.info("Bridge Model belum menghasilkan output.")
                else:
                    st.caption(f"Jumlah Pilihan Bridge: {len(bridge_df)}")
                    copy_button_clean("📋 Copy Bridge V1", bridge_text, "bridge_model_v31_9")
                    with st.expander("Lihat Detail Bridge V1", expanded=False):
                        st.markdown("**Base Pair**")
                        st.dataframe(bridge_pair_df, hide_index=True, use_container_width=True)
                        st.markdown("**Senarai Bridge**")
                        st.dataframe(bridge_df, hide_index=True, use_container_width=True)
                    render_bridge_pair_choices(
                        bridge_pair_df, bridge_df, "Bridge V1", "main_pair_v1", draw=(first, second, third)
                    )
            except Exception as e:
                st.warning(f"Bridge Model belum dapat dipaparkan: {e}")

        # -----------------------------
        # Bridge Engine V2 - Pair + 2D Missing / Pair + 2D Existing
        # -----------------------------
        with tab_v2:
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
                        f"Jumlah pilihan unik: {len(bridge_v2_df)} | "
                        f"2 Missing: {v2_missing_count} | 2 Existing: {v2_existing_count}"
                    )
                    copy_button_clean("📋 Copy Bridge V2", bridge_v2_text, "bridge_engine_v2_double_digit")
                    with st.expander("Lihat Detail Bridge V2", expanded=False):
                        st.markdown("**Base Pair**")
                        st.dataframe(
                            bridge_v2_pair_df, hide_index=True, use_container_width=True
                        )
                        st.markdown("**Senarai Bridge**")
                        st.dataframe(bridge_v2_df, hide_index=True, use_container_width=True)
                    render_bridge_pair_choices(
                        bridge_v2_pair_df, bridge_v2_df, "Bridge V2", "main_pair_v2", draw=(first, second, third)
                    )
            except Exception as e:
                st.warning(f"Bridge Engine V2 belum dapat dipaparkan: {e}")

        # -----------------------------
        # Route Signal: satu pilihan ringkas berdasarkan tiga hadiah.
        # -----------------------------
        try:
            with tab_route:
                def build_dynamic_match_route_signal(
                    first_no, second_no, third_no, current_counts,
                    sample_size=8, recent_window=30, min_margin=0.035,
                ):
                    """Pilih Bridge dahulu, kemudian aras dalam Bridge yang dipilih."""
                    route_names = (
                        "Solo V1", "Solo V2",
                        "Double Match V1", "Double Match V2",
                        "Triple Match V1", "Triple Match V2",
                        "Quattro Match V1", "Quattro Match V2",
                    )

                    def result_state(result_text):
                        values = [_pad4(value.strip()) for value in result_text.split("/")]
                        joined = "".join(values)
                        return (
                            10 - len(set(joined)),
                            len(set(values[0])), len(set(values[1])), len(set(values[2])),
                            sum(len(set(value)) < 4 for value in values),
                        )

                    count_columns = (
                        "Bridge Count", "Bridge V2 Count",
                        "1st2D+Missing2nd Candidate Count",
                        "1st2D+Missing3rd Candidate Count",
                        "1st2D+2nd3rd Candidate Count",
                        "2D+Missing Candidate Count",
                        "2D+1st3rd Candidate Count",
                        "3rd2D+Missing Candidate Count",
                        "3rd2D+1st2nd Candidate Count",
                    )

                    def safe_float(value):
                        try:
                            return float(value or 0)
                        except (TypeError, ValueError):
                            return 0.0

                    def engine_state(row):
                        source_result = str(row.get("Source Result", ""))
                        base = result_state(source_result)
                        counts = tuple(
                            math.log1p(safe_float(row.get(column)))
                            for column in count_columns
                        )
                        values = [_pad4(value.strip()) for value in source_result.split("/")]
                        joined = "".join(values)
                        frequencies = tuple(
                            joined.count(str(digit)) / 12 for digit in range(10)
                        )
                        return base + counts + frequencies

                    def state_distance(left, right):
                        scales = (2, 2, 2, 2, 2) + (2,) * len(count_columns) + (0.35,) * 10
                        return sum(
                            abs(current - historical) / scale
                            for current, historical, scale in zip(left, right, scales)
                        )

                    def hit_families(row, column):
                        text_value = str(row.get(f"{column} Hit Number", "") or "")
                        return {
                            _key4(value.strip())
                            for value in text_value.split("/") if value.strip()
                        }

                    def match_outcomes(row):
                        bridge_v1 = hit_families(row, "Bridge")
                        bridge_v2 = hit_families(row, "Bridge V2")
                        engines_v1 = (
                            hit_families(row, "1st2D+Missing2nd Bridge") |
                            hit_families(row, "1st2D+Missing3rd Bridge"),
                            hit_families(row, "2D+Missing"),
                            hit_families(row, "3rd2D+Missing Bridge"),
                        )
                        engines_v2 = (
                            hit_families(row, "1st2D+2nd3rd Bridge"),
                            hit_families(row, "2D+1st3rd"),
                            hit_families(row, "3rd2D+1st2nd Bridge"),
                        )
                        outcomes = {}
                        for version, bridge_set, engine_sets in (
                            ("V1", bridge_v1, engines_v1),
                            ("V2", bridge_v2, engines_v2),
                        ):
                            support = {
                                family: sum(family in engine_set for engine_set in engine_sets)
                                for family in bridge_set
                            }
                            outcomes[f"Solo {version}"] = any(
                                count == 0 for count in support.values()
                            )
                            outcomes[f"Double Match {version}"] = any(
                                count == 1 for count in support.values()
                            )
                            outcomes[f"Triple Match {version}"] = any(
                                count == 2 for count in support.values()
                            )
                            outcomes[f"Quattro Match {version}"] = any(
                                count == 3 for count in support.values()
                            )
                        return outcomes

                    cache_path = Path(".backtest_row_cache_v31_54_first_routes.json")
                    cache_rows = []
                    try:
                        if cache_path.exists():
                            cache_rows = list(
                                json.loads(cache_path.read_text(encoding="utf-8"))
                                .get("rows", {}).values()
                            )[-100:]
                    except Exception:
                        cache_rows = []

                    # Streamlit Cloud boleh membuang fail cache tempatan ketika restart.
                    # Bina semula bukti terus daripada history; jangan tukar signal kepada
                    # Seimbang hanya kerana fail tersembunyi tidak tersedia.
                    if not cache_rows:
                        _, rebuilt_detail = run_backtest_bridge_dde_lite_v31_24_5(
                            st.session_state.history, test_draws=min(
                                101, len(st.session_state.history)
                            )
                        )
                        if rebuilt_detail is not None and not rebuilt_detail.empty:
                            rebuilt_rows = rebuilt_detail.to_dict("records")
                            cache_rows = [
                                row for row in rebuilt_rows
                                if str(row.get("Next Result", "")).strip()
                                and str(row.get("Next Result", "")).strip()
                                != "Belum ada next draw"
                            ][-100:]
                    if not cache_rows:
                        return {
                            "signal": "Tiada Laluan Jelas", "sample": 0,
                            "scores": {}, "margin": 0.0,
                        }

                    current_row = dict(current_counts)
                    current_row["Source Result"] = (
                        f"{_pad4(first_no)} / {_pad4(second_no)} / {_pad4(third_no)}"
                    )
                    current_state = engine_state(current_row)
                    evidence = []
                    for sequence, row in enumerate(cache_rows):
                        try:
                            historical_state = engine_state(row)
                        except Exception:
                            continue
                        distance = state_distance(current_state, historical_state)
                        evidence.append((distance, -sequence, match_outcomes(row)))
                    evidence.sort(key=lambda item: (item[0], item[1]))
                    nearest = evidence[:min(sample_size, len(evidence))]
                    if not nearest:
                        return {
                            "signal": "Tiada Laluan Jelas", "sample": 0,
                            "scores": {}, "margin": 0.0,
                        }
                    # Tahap 1: nilai V1 dan V2 secara simetri. Versi yang kalah tidak
                    # dibuang apabila jurang keadaan masih rapat atau sokongannya masih
                    # munasabah; ia dibawa sebagai laluan keselamatan.
                    bridge_scores = {}
                    for version in ("V1", "V2"):
                        version_routes = [name for name in route_names if name.endswith(version)]
                        bridge_scores[version] = sum(
                            (1.0 / (1.0 + distance)) * int(
                                any(outcomes.get(name, False) for name in version_routes)
                            )
                            for distance, _, outcomes in nearest
                        ) / max(0.000001, sum(1.0 / (1.0 + item[0]) for item in nearest))
                    chosen_version = max(bridge_scores, key=bridge_scores.get)
                    other_version = "V2" if chosen_version == "V1" else "V1"
                    bridge_gap = bridge_scores[chosen_version] - bridge_scores[other_version]
                    bridge_is_balanced = (
                        bridge_gap < 0.30 or bridge_scores[other_version] >= 0.40
                    )

                    # Tahap 2: hanya bandingkan Solo/Double/Triple/Quattro dalam Bridge
                    # yang sudah dipilih. Ini mengelakkan V1 dan V2 makan sesama sendiri.
                    scores = {}
                    best_by_version = {}
                    margin_by_version = {}
                    ordered_by_version = {}
                    for version in ("V1", "V2"):
                        version_routes = [name for name in route_names if name.endswith(version)]
                        level_nearest = [
                            item for item in evidence
                            if any(item[2].get(name, False) for name in version_routes)
                        ][:min(sample_size, len(evidence))]
                        total_weight = sum(1.0 / (1.0 + item[0]) for item in level_nearest)
                        for route in version_routes:
                            scores[route] = sum(
                                (1.0 / (1.0 + distance)) * int(outcomes.get(route, False))
                                for distance, _, outcomes in level_nearest
                            ) / max(0.000001, total_weight)
                        ordered_version = sorted(
                            version_routes, key=lambda name: scores.get(name, 0), reverse=True
                        )
                        ordered_by_version[version] = ordered_version
                        best_by_version[version] = ordered_version[0]
                        margin_by_version[version] = (
                            scores[ordered_version[0]] - scores[ordered_version[1]]
                            if len(ordered_version) > 1 else scores[ordered_version[0]]
                        )

                    signal = best_by_version[chosen_version]
                    margin = margin_by_version[chosen_version]
                    if bridge_is_balanced:
                        # Dalam keadaan seimbang, Solo terlalu mudah menang hanya
                        # kerana bilangannya besar. Dahulukan laluan yang benar-benar
                        # menerima sokongan engine (Double/Triple/Quattro), merentas
                        # V1 dan V2. Solo kekal sebagai pilihan terakhir sahaja.
                        match_routes = [
                            name for name in route_names
                            if not name.startswith("Solo") and scores.get(name, 0) > 0
                        ]
                        match_routes.sort(key=lambda name: scores.get(name, 0), reverse=True)
                        if match_routes:
                            signal = match_routes[0]
                            margin = (
                                scores[match_routes[0]] - scores[match_routes[1]]
                                if len(match_routes) > 1 else scores[match_routes[0]]
                            )
                    elif margin < min_margin:
                        signal = "Tiada Laluan Jelas"
                    safety_signals = []
                    if bridge_is_balanced:
                        # Keadaan seimbang tidak boleh bergantung pada satu laluan
                        # keselamatan sahaja. Kekalkan dua tahap terdekat daripada
                        # Bridge sebelah supaya Double dan Triple tidak saling membuang.
                        for safety_signal in ordered_by_version.get(other_version, []):
                            if (
                                safety_signal != signal
                                and scores.get(safety_signal, 0) > 0
                            ):
                                safety_signals.append(safety_signal)
                            if len(safety_signals) >= 2:
                                break
                    return {
                        "signal": signal, "sample": len(nearest),
                        "scores": scores, "margin": margin,
                        "bridge": chosen_version,
                        "bridge_label": (
                            "Seimbang (V1 + V2)"
                            if bridge_is_balanced else chosen_version
                        ),
                        "bridge_scores": bridge_scores,
                        "bridge_gap": bridge_gap,
                        "safety_signals": safety_signals,
                    }

                def unique_generated_count(frame):
                    if frame is None or frame.empty or "No Terhasil" not in frame.columns:
                        return 0
                    return len({_key4(number) for number in frame["No Terhasil"].astype(str)})

                # Kira keadaan calon semasa menggunakan formula engine yang sama.
                current_first_missing = build_1st_missing_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                current_first_pair = build_1st_second_third_pair_engine(
                    st.session_state.history, first, second, third, lookback=100,
                )
                current_second_missing = build_2d_missing_first_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                current_second_pair = build_2d_first_third_pair_engine(
                    st.session_state.history, first, second, third, lookback=100,
                )
                current_third_missing = build_3rd_missing_first_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                current_third_pair = build_3rd_first_second_pair_engine(
                    st.session_state.history, first, second, third, lookback=100,
                )
                first_all = current_first_missing.get("all", pd.DataFrame())
                current_counts = {
                    "Bridge Count": len(bridge_df),
                    "Bridge V2 Count": len(bridge_v2_df),
                    "1st2D+Missing2nd Candidate Count": unique_generated_count(
                        first_all[first_all["Sumber Digit"].eq("Digit 2nd")]
                        if not first_all.empty and "Sumber Digit" in first_all.columns
                        else pd.DataFrame()
                    ),
                    "1st2D+Missing3rd Candidate Count": unique_generated_count(
                        first_all[first_all["Sumber Digit"].eq("Digit 3rd")]
                        if not first_all.empty and "Sumber Digit" in first_all.columns
                        else pd.DataFrame()
                    ),
                    "1st2D+2nd3rd Candidate Count": unique_generated_count(current_first_pair.get("all")),
                    "2D+Missing Candidate Count": unique_generated_count(current_second_missing.get("all")),
                    "2D+1st3rd Candidate Count": unique_generated_count(current_second_pair.get("all")),
                    "3rd2D+Missing Candidate Count": unique_generated_count(current_third_missing.get("all")),
                    "3rd2D+1st2nd Candidate Count": unique_generated_count(current_third_pair.get("all")),
                }

                first_route_signal = build_1st_route_signal(
                    st.session_state.history, first, second, third, lookback=100
                )
                route_signal = build_2d_route_signal(
                    st.session_state.history, first, second, third, lookback=100
                )
                third_route_signal = build_3rd_route_signal(
                    st.session_state.history, first, second, third, lookback=100
                )
                first_route_version = {
                    "1st 2D + Missing": "V1",
                    "1st 2D + 2nd & 3rd": "V2",
                }.get(first_route_signal["signal"])
                second_route_version = {
                    "2D + Missing": "V1",
                    "2D + 1st & 3rd": "V2",
                }.get(route_signal["signal"])
                third_route_version = {
                    "3rd 2D + Missing": "V1",
                    "3rd 2D + 1st & 2nd": "V2",
                }.get(third_route_signal["signal"])
                dynamic_match_signal = build_dynamic_match_route_signal(
                    first, second, third, current_counts,
                    sample_size=8, recent_window=30, min_margin=0.035,
                )
                match_route_text = dynamic_match_signal["signal"]

                with summary_box:
                    st.markdown('<div class="rap-panel-title">Ringkasan Signal</div>', unsafe_allow_html=True)
                    st.caption(f"Hasil untuk: {first} / {second} / {third}")
                    def _tile(label, sig):
                        text = sig["signal"]
                        if text == "Seimbang":
                            return {"label": label, "value": "-", "kind": "Tiada pilihan", "support": 0, "none": True}
                        is_v1 = str(text).endswith("Missing")
                        return {"label": label, "value": "V1" if is_v1 else "V2",
                                "kind": "Missing" if is_v1 else "Pair", "support": int(sig.get("support", 0))}

                    st.markdown(
                        signal_tiles_html([
                            _tile("1st Prize", first_route_signal),
                            _tile("2nd Prize", route_signal),
                            _tile("3rd Prize", third_route_signal),
                        ]),
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        info_row_html([
                            ("Bridge", dynamic_match_signal.get("bridge_label", dynamic_match_signal.get("bridge", "Tiada"))),
                            ("Laluan", match_route_text),
                        ]),
                        unsafe_allow_html=True,
                    )
                st.markdown(f"**Bridge Pilihan:** {dynamic_match_signal.get('bridge_label', dynamic_match_signal.get('bridge', 'Tiada'))} ")
                st.markdown(f"**Laluan Pilihan:** {match_route_text}")
                safety_route_texts = dynamic_match_signal.get("safety_signals", [])
                if safety_route_texts:
                    st.markdown(f"**Laluan Keselamatan:** {' / '.join(safety_route_texts)}")
                if match_route_text == "Tiada Laluan Jelas":
                    match_scores = dynamic_match_signal.get("scores", {})
                    if match_scores:
                        suggested_match = max(match_scores, key=match_scores.get)
                    else:
                        suggested_match = "Tiada"
                    suggested_version = (
                        "V1" if suggested_match.endswith("V1")
                        else "V2" if suggested_match.endswith("V2")
                        else None
                    )
                    engine_options = [
                        (first_route_signal.get("signal", "Seimbang"), int(first_route_signal.get("support", 0)), first_route_version),
                        (route_signal.get("signal", "Seimbang"), int(route_signal.get("support", 0)), second_route_version),
                        (third_route_signal.get("signal", "Seimbang"), int(third_route_signal.get("support", 0)), third_route_version),
                    ]
                    valid_engine_options = [
                        (name, support) for name, support, version in engine_options
                        if name != "Seimbang" and support > 0
                        and version == suggested_version
                    ]
                    if valid_engine_options:
                        suggested_engine = max(
                            valid_engine_options, key=lambda item: item[1]
                        )[0]
                    else:
                        suggested_engine = "Tiada"
                    st.markdown(
                        f"**Cadangan Match terdekat:** {suggested_match}"
                    )
                    st.markdown(
                        f"**Cadangan Engine:** {suggested_engine}"
                    )
                with st.expander("Lihat asas Route Signal", expanded=False):
                    st.markdown(f"1st: {first_route_signal['signal']}")
                    st.markdown(f"2nd: {route_signal['signal']}")
                    st.markdown(f"3rd: {third_route_signal['signal']}")
                    st.markdown(
                        f"Keadaan sejarah dibandingkan: {dynamic_match_signal['sample']}"
                    )
                    for bridge_name, bridge_score in dynamic_match_signal.get("bridge_scores", {}).items():
                        st.markdown(f"Bridge {bridge_name}: {bridge_score * 100:.1f}%")
                    for route_name, route_hits in dynamic_match_signal["scores"].items():
                        st.markdown(
                            f"{route_name}: {route_hits * 100:.1f}%"
                        )
                    st.markdown(
                        f"Margin keyakinan: {dynamic_match_signal.get('margin', 0) * 100:.1f}%"
                    )

                v1_route_lookup = {
                    _key4(number): _pad4(number)
                    for number in bridge_df.get("No", pd.Series(dtype=str)).astype(str)
                } if bridge_df is not None and not bridge_df.empty else {}
                v2_route_lookup = {
                    _key4(number): _pad4(number)
                    for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
                } if bridge_v2_df is not None and not bridge_v2_df.empty else {}

                def bridge_route_numbers(families, bridge="both"):
                    numbers = []
                    seen = set()
                    for family in families:
                        if family in seen:
                            continue
                        if bridge == "V1":
                            bridge_number = v1_route_lookup.get(family)
                        elif bridge == "V2":
                            bridge_number = v2_route_lookup.get(family)
                        else:
                            bridge_number = v1_route_lookup.get(family) or v2_route_lookup.get(family)
                        if not bridge_number:
                            continue
                        seen.add(family)
                        numbers.append(bridge_number)
                    return numbers

                first_missing_route = build_1st_missing_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                first_pair_route = build_1st_second_third_pair_engine(
                    st.session_state.history, first, second, third, lookback=100,
                )

                missing_route = build_2d_missing_first_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                current_second = _pad4(second)
                current_first = _pad4(first)
                missing_families = []
                for _, audit_row in missing_route["joint_audit"].iterrows():
                    left, right = [
                        int(value) - 1
                        for value in str(audit_row["Kedudukan 2D"]).split("+")
                    ]
                    duo = current_second[left] + current_second[right]
                    first_digit = current_first[
                        int(audit_row["Kedudukan Digit 1st"]) - 1
                    ]
                    for missing in missing_route["missing"]:
                        missing_families.append(
                            _key4(f"{duo}{missing}{first_digit}")
                        )

                first_third_extended = build_first_third_extended_audit(
                    st.session_state.history, first, second, third, lookback=100
                )

                third_missing_route = build_3rd_missing_first_digit_engine(
                    st.session_state.history, first, second, third,
                    bridge_df, bridge_v2_df, lookback=100,
                )
                current_third = _pad4(third)
                third_missing_families = []
                for _, audit_row in third_missing_route["joint_audit"].iterrows():
                    left, right = [
                        int(value) - 1
                        for value in str(audit_row["Kedudukan 3rd 2D"]).split("+")
                    ]
                    duo = current_third[left] + current_third[right]
                    first_digit = current_first[
                        int(audit_row["Kedudukan Digit 1st"]) - 1
                    ]
                    for missing in third_missing_route["missing"]:
                        third_missing_families.append(_key4(f"{duo}{missing}{first_digit}"))

                third_first_second_route = build_3rd_first_second_pair_engine(
                    st.session_state.history, first, second, third, lookback=100,
                )

                # Butiran laluan lama disimpan sebagai rujukan dalaman dan tidak dirender.
                # -----------------------------
                # Engine Consensus Tanpa Bridge
                # -----------------------------
                # Kekalkan objek ini untuk Match V2; paparan Consensus lama dinyahaktifkan.
                second_first_third_route = build_2d_first_third_pair_engine(
                    st.session_state.history, first, second, third, lookback=100
                )

                # Top-N: calon laluan terpilih digabung, satu baris bagi setiap keluarga box.
                selected_route_frames = {}
                for _name, _signal, _wanted, _obj in (
                    ("1st V1", first_route_signal["signal"], "1st 2D + Missing", first_missing_route),
                    ("1st V2", first_route_signal["signal"], "1st 2D + 2nd & 3rd", first_pair_route),
                    ("2nd V1", route_signal["signal"], "2D + Missing", missing_route),
                    ("2nd V2", route_signal["signal"], "2D + 1st & 3rd", second_first_third_route),
                    ("3rd V1", third_route_signal["signal"], "3rd 2D + Missing", third_missing_route),
                    ("3rd V2", third_route_signal["signal"], "3rd 2D + 1st & 2nd", third_first_second_route),
                ):
                    if _signal == _wanted:
                        selected_route_frames[_name] = _obj.get("all", pd.DataFrame())
                route_support_map = {
                    "1st V1": first_route_signal.get("support", 0), "1st V2": first_route_signal.get("support", 0),
                    "2nd V1": route_signal.get("support", 0), "2nd V2": route_signal.get("support", 0),
                    "3rd V1": third_route_signal.get("support", 0), "3rd V2": third_route_signal.get("support", 0),
                }
                with summary_box:
                    route_top_n = st.selectbox(
                        "Bilangan nombor route terpilih",
                        [5, 10, 15, 20, 30],
                        index=1,
                        format_func=lambda value: f"Top {value}",
                        key="route_top_n_choice",
                    )
                    route_shortlist_df = rank_candidates_consensus(
                        selected_route_frames, route_support_map, top_n=route_top_n
                    )
                    if route_shortlist_df.empty:
                        st.info("Tiada laluan jelas untuk disenaraikan pada draw ini.")
                    else:
                        st.markdown(f"**Top {len(route_shortlist_df)} nombor route terpilih**")
                        show_numbers(route_shortlist_df["Calon"].astype(str).tolist(), "route_topn", highlight=3)
                        st.caption(
                            "Disusun ikut skor konsensus (bilangan route yang menjana + sokongan keadaan draw). "
                            "Cabutan sebenar tetap rawak; ini bukan jaminan."
                        )
                        with st.expander("Lihat jadual skor", expanded=False):
                            st.dataframe(route_shortlist_df, hide_index=True, use_container_width=True)
                # Match 4-laluan dikira dahulu; ringkasan laluan dipaparkan sebelum panel Match.

                def _route_family_set(frame):
                    if frame is None or frame.empty or "No Terhasil" not in frame.columns:
                        return set()
                    return {
                        _key4(number)
                        for number in frame["No Terhasil"].dropna().astype(str)
                    }

                def _ordered_route_numbers(families, lookup):
                    wanted = set(families)
                    return [
                        number for family, number in lookup.items()
                        if family in wanted
                    ]

                first_missing_all_families = _route_family_set(first_missing_route["all"])
                first_pair_all_families = _route_family_set(first_pair_route["all"])
                second_missing_families = _route_family_set(missing_route["all"])
                third_missing_all_families = _route_family_set(third_missing_route["all"])
                first_third_all_engine = second_first_third_route
                second_first_third_families = _route_family_set(
                    first_third_all_engine["all"]
                )
                third_first_second_all_families = _route_family_set(
                    third_first_second_route["all"]
                )

                v1_bridge_families = set(v1_route_lookup)
                v1_first = v1_bridge_families & first_missing_all_families
                v1_second = v1_bridge_families & second_missing_families
                v1_third = v1_bridge_families & third_missing_all_families
                v1_support = Counter(
                    family for route_set in (v1_first, v1_second, v1_third)
                    for family in route_set
                )
                v1_triple = {family for family, count in v1_support.items() if count == 3}
                v1_double_only = {family for family, count in v1_support.items() if count == 2}
                v1_single_only = {family for family, count in v1_support.items() if count == 1}
                v1_solo = v1_bridge_families - set(v1_support)

                v2_bridge_families = set(v2_route_lookup)
                v2_first = v2_bridge_families & first_pair_all_families
                v2_second = v2_bridge_families & second_first_third_families
                v2_third = v2_bridge_families & third_first_second_all_families
                v2_support = Counter(
                    family for route_set in (v2_first, v2_second, v2_third)
                    for family in route_set
                )
                v2_triple = {family for family, count in v2_support.items() if count == 3}
                v2_double_only = {family for family, count in v2_support.items() if count == 2}
                v2_single_only = {family for family, count in v2_support.items() if count == 1}
                v2_solo = v2_bridge_families - set(v2_support)

                v1_triple_numbers = _ordered_route_numbers(v1_triple, v1_route_lookup)
                v2_triple_numbers = _ordered_route_numbers(v2_triple, v2_route_lookup)
                v1_double_numbers = _ordered_route_numbers(v1_double_only, v1_route_lookup)
                v2_double_numbers = _ordered_route_numbers(v2_double_only, v2_route_lookup)
                v1_single_numbers = _ordered_route_numbers(v1_single_only, v1_route_lookup)
                v2_single_numbers = _ordered_route_numbers(v2_single_only, v2_route_lookup)
                v1_solo_numbers = _ordered_route_numbers(v1_solo, v1_route_lookup)
                v2_solo_numbers = _ordered_route_numbers(v2_solo, v2_route_lookup)

                # Satu ranking 2D yang sama digunakan pada semua senarai Match.
                # Ia hanya mengubah susunan paparan; tiada nombor ditambah atau dibuang.
                current_2d_ranking = build_current_2d_ranking(
                    st.session_state.history, first, second, third, lookback=100
                )
                v1_triple_numbers = sort_match_numbers_by_2d(
                    v1_triple_numbers, current_2d_ranking
                )
                v2_triple_numbers = sort_match_numbers_by_2d(
                    v2_triple_numbers, current_2d_ranking
                )
                v1_double_numbers = sort_match_numbers_by_2d(
                    v1_double_numbers, current_2d_ranking
                )
                v2_double_numbers = sort_match_numbers_by_2d(
                    v2_double_numbers, current_2d_ranking
                )
                v1_single_numbers = sort_match_numbers_by_2d(
                    v1_single_numbers, current_2d_ranking
                )
                v2_single_numbers = sort_match_numbers_by_2d(
                    v2_single_numbers, current_2d_ranking
                )
                v1_solo_numbers = sort_match_numbers_by_2d(
                    v1_solo_numbers, current_2d_ranking
                )
                v2_solo_numbers = sort_match_numbers_by_2d(
                    v2_solo_numbers, current_2d_ranking
                )

                route_number_map = {
                    "Solo V1": v1_solo_numbers,
                    "Solo V2": v2_solo_numbers,
                    "Quattro Match V1": v1_triple_numbers,
                    "Quattro Match V2": v2_triple_numbers,
                    "Triple Match V1": v1_double_numbers,
                    "Triple Match V2": v2_double_numbers,
                    "Double Match V1": v1_single_numbers,
                    "Double Match V2": v2_single_numbers,
                }
                route_choice_numbers = route_number_map.get(match_route_text, [])

                if route_choice_numbers:
                    with st.expander(
                        f"Lihat nombor {match_route_text} ({len(route_choice_numbers)})",
                        expanded=False,
                    ):
                        st.markdown(f"{' / '.join(route_choice_numbers)}")
                        copy_button_clean(
                            "📋 Copy",
                            "Rumah A Predictor - Route Signal\n\n"
                            f"Laluan: {match_route_text}\n"
                            f"Jumlah Pilihan: {len(route_choice_numbers)}\n"
                            f"{' / '.join(route_choice_numbers)}",
                            "copy_dynamic_route_full",
                        )

                for safety_index, safety_route in enumerate(safety_route_texts, start=1):
                    safety_numbers = route_number_map.get(safety_route, [])
                    if not safety_numbers:
                        continue
                    with st.expander(
                        f"Lihat nombor keselamatan {safety_route} ({len(safety_numbers)})",
                        expanded=False,
                    ):
                        st.markdown(f"{' / '.join(safety_numbers)}")
                        copy_button_clean(
                            "📋 Copy",
                            "Rumah A Predictor - Route Signal Keselamatan\n\n"
                            f"Laluan: {safety_route}\n"
                            f"Jumlah Pilihan: {len(safety_numbers)}\n"
                            f"{' / '.join(safety_numbers)}",
                            f"copy_dynamic_route_safety_{safety_index}",
                        )

                with tab_match:
                    match_levels = [
                        ("Quattro Match", "4/4", "Bridge + 3 engine", v1_triple_numbers, v2_triple_numbers),
                        ("Triple Match", "3/4", "Bridge + 2 engine", v1_double_numbers, v2_double_numbers),
                        ("Double Match", "2/4", "Bridge + 1 engine", v1_single_numbers, v2_single_numbers),
                        ("Bridge Solo", "1/4", "Bridge tanpa sokongan engine", v1_solo_numbers, v2_solo_numbers),
                    ]
                    st.markdown(f"**Laluan dipilih signal:** {match_route_text}")
                    st.dataframe(
                        pd.DataFrame([
                            {"Tahap": name, "Sokongan": level, "Maksud": meaning, "V1": len(v1), "V2": len(v2)}
                            for name, level, meaning, v1, v2 in match_levels
                        ]),
                        hide_index=True, use_container_width=True,
                    )
                    default_level = next(
                        (n for n, (name, *_rest) in enumerate(match_levels) if name in str(match_route_text)), 0
                    )
                    level_labels = [f"{name} ({level})" for name, level, *_rest in match_levels]
                    level_a, level_b = st.columns([2, 1])
                    level_choice = level_a.selectbox(
                        "Pilih tahap", level_labels, index=default_level, key="match_level_choice"
                    )
                    match_limit = level_b.selectbox(
                        "Had nombor", [20, 50, 100, 0], index=0,
                        format_func=lambda value: "Semua" if value == 0 else f"Top {value}",
                        key="match_level_limit",
                    )
                    chosen_name, _lv, _meaning, chosen_v1, chosen_v2 = match_levels[level_labels.index(level_choice)]
                    for version, numbers in (("V1", chosen_v1), ("V2", chosen_v2)):
                        shown_numbers = list(numbers)[: (match_limit or None)]
                        st.markdown(f"**{chosen_name} {version}** ({len(numbers)} nombor)")
                        show_numbers(shown_numbers, f"match_{chosen_name}_{version}")
        except Exception as e:
            st.warning(f"Route Signal / Quattro Match belum dapat dipaparkan: {e}")

        with tab_adv:
            def _show_uniform_2d_audit(audit_df, position_columns, source_text):
                """Paparan audit seragam; formula dan pemilihan engine kekal."""
                view = audit_df.copy() if audit_df is not None else pd.DataFrame()
                if view.empty:
                    st.info("Tiada rekod audit untuk laluan ini.")
                    return
                for column in position_columns:
                    if column in view.columns:
                        view = view.rename(columns={column: "Kedudukan 2D"})
                        break
                if "Sumber Digit" not in view.columns:
                    view.insert(1 if "Kedudukan 2D" in view.columns else 0,
                                "Sumber Digit", source_text)
                preferred = ["Kedudukan 2D", "Sumber Digit", "Kedudukan Digit",
                             "Kedudukan Digit 1st", "Hit Draw", "Draw Diuji",
                             "Hit Rate %", "Pilihan Semasa"]
                columns = [column for column in preferred if column in view.columns]
                st.dataframe(view[columns] if columns else view, hide_index=True,
                             use_container_width=True)

            # -----------------------------
            # Top 2D Engine - 1st Prize
            # -----------------------------
            st.markdown(
                '<div class="engine-head engine-support">1st 2D Engine</div>',
                unsafe_allow_html=True,
            )
            try:
                first_missing_engine = first_missing_route
                source_text = " / ".join(first_missing_engine["selected_sources"]) or "Tiada"
                position_text = " / ".join(first_missing_engine["selected_positions"]) or "Tiada"
                digit_text = " / ".join(dict.fromkeys(
                    f"{item['Sumber Digit']} posisi {item['Kedudukan Digit']}"
                    for item in first_missing_engine["selected_digits"]
                )) or "Tiada"
                first_v1_numbers = list(dict.fromkeys(
                    number for number in first_missing_engine["selected"].get(
                        "Bridge V1", pd.Series(dtype=str)
                    ).astype(str) if number.strip()
                ))
                st.markdown("**1st 2D + Missing**")
                st.markdown(
                    f"1st 2D: {position_text} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Sumber digit: {source_text}"
                )
                st.markdown(f"**Pilihan Bridge V1 ({len(first_v1_numbers)}):** "
                            f"{' / '.join(first_v1_numbers) or 'Tiada'}")
                copy_button_clean(
                    "📋 Copy",
                    "Rumah A Predictor - 1st 2D + Missing\n\n"
                    f"1st 2D: {position_text}\nSumber digit: {source_text}\n"
                    f"Kedudukan digit: {digit_text}\n"
                    f"Jumlah Pilihan Bridge V1: {len(first_v1_numbers)}\n"
                    f"{' / '.join(first_v1_numbers) or 'Tiada'}",
                    "copy_first_2d_missing",
                )
                first_missing_pair_df = first_missing_engine["all"].copy()
                if not first_missing_pair_df.empty:
                    first_missing_pair_df = first_missing_pair_df[
                        first_missing_pair_df["Bridge V1"].fillna("").astype(str).str.strip().ne("")
                    ].copy()
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(
                        dict.fromkeys(first_missing_pair_df["1st 2D"].astype(str)), start=1
                    ):
                        pair_df = first_missing_pair_df[
                            first_missing_pair_df["1st 2D"].astype(str).eq(pair_value)
                        ].copy()
                        pair_numbers = list(dict.fromkeys(
                            pair_df["Bridge V1"].astype(str).tolist()
                        ))
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan 1st 2D"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_1")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        first_missing_engine["joint_audit"],
                        ["Kedudukan 1st 2D", "Kedudukan 2D"], source_text,
                    )

                first_pair_engine = first_pair_route
                first_pair_positions = " / ".join(
                    first_pair_engine["selected_positions"]
                ) or "Tiada"
                v2_lookup = {
                    _key4(number): _pad4(number)
                    for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
                } if bridge_v2_df is not None and not bridge_v2_df.empty else {}
                first_v2_numbers = list(dict.fromkeys(
                    v2_lookup.get(_key4(number), "")
                    for number in first_pair_engine["selected"].get(
                        "No Terhasil", pd.Series(dtype=str)
                    ).astype(str)
                    if v2_lookup.get(_key4(number), "")
                ))
                st.divider()
                st.markdown("**1st 2D + Digit 2nd & 3rd**")
                st.markdown(f"1st 2D: {first_pair_positions}")
                st.markdown(f"**Pilihan Bridge V2 ({len(first_v2_numbers)}):** "
                            f"{' / '.join(first_v2_numbers) or 'Tiada'}")
                copy_button_clean(
                    "📋 Copy",
                    "Rumah A Predictor - 1st 2D + Digit 2nd & 3rd\n\n"
                    f"1st 2D: {first_pair_positions}\n"
                    f"Jumlah Pilihan Bridge V2: {len(first_v2_numbers)}\n"
                    f"{' / '.join(first_v2_numbers) or 'Tiada'}",
                    "copy_first_2d_second_third",
                )
                first_pair_all_df = first_pair_engine["all"].copy()
                if not first_pair_all_df.empty:
                    first_pair_all_df["Bridge V2"] = first_pair_all_df["No Terhasil"].map(
                        lambda number: v2_lookup.get(_key4(number), "")
                    )
                    first_pair_all_df = first_pair_all_df[
                        first_pair_all_df["Bridge V2"].astype(str).str.strip().ne("")
                    ].copy()
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(
                        dict.fromkeys(first_pair_all_df["1st 2D"].astype(str)), start=1
                    ):
                        pair_df = first_pair_all_df[
                            first_pair_all_df["1st 2D"].astype(str).eq(pair_value)
                        ].copy()
                        pair_numbers = list(dict.fromkeys(pair_df["Bridge V2"].astype(str)))
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan 1st 2D"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_2")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        first_pair_engine["audit"],
                        ["Kedudukan 1st 2D", "Kedudukan 2D"], "Digit 2nd & 3rd",
                    )
            except Exception as e:
                st.warning(f"Top 2D Engine belum dapat dipaparkan: {e}")

            # -----------------------------
            # 2D + Missing + Digit 1st
            # -----------------------------
            st.markdown(
                '<div class="engine-head engine-support">2nd 2D Engine</div>',
                unsafe_allow_html=True,
            )
            st.markdown("**2nd 2D + Missing**")
            try:
                route_engine = missing_route
                all_route_df = route_engine["all"]
                selected_first_positions = {1, 2, 3, 4}
                all_pair_view = all_route_df[
                    all_route_df["Kedudukan Digit 1st"].isin(selected_first_positions)
                ].copy() if not all_route_df.empty else all_route_df.copy()
                all_numbers = (
                    list(dict.fromkeys(all_pair_view["No Terhasil"].astype(str).tolist()))
                    if not all_pair_view.empty else []
                )
                selected_second_text = " / ".join(route_engine["selected_second"]) or "Tiada"

                # Padankan setiap laluan audit dengan nombor draw semasa supaya
                # keputusan audit boleh terus dibaca tanpa mengira secara manual.
                current_second = _pad4(second)
                current_first = _pad4(first)
                joint_view = route_engine["joint_audit"].copy()
                joint_current_numbers = []
                for _, audit_row in joint_view.iterrows():
                    position_parts = [
                        int(value) - 1
                        for value in str(audit_row["Kedudukan 2D"]).split("+")
                    ]
                    duo = "".join(current_second[position] for position in position_parts)
                    first_digit = current_first[
                        int(audit_row["Kedudukan Digit 1st"]) - 1
                    ]
                    numbers = [
                        f"{duo}{missing}{first_digit}"
                        for missing in route_engine["missing"]
                    ]
                    joint_current_numbers.append(" / ".join(numbers) or "Tiada")
                joint_view["Pilihan Semasa"] = joint_current_numbers


                st.markdown(
                    f"2nd 2D: {selected_second_text} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    "Sumber digit: Digit 1st"
                )


                # Semua pair unik daripada enam kedudukan 2nd Prize. Pair yang sama
                # digabungkan, tetapi asal kedudukannya masih dipaparkan.
                # Senarai mentah semua pair tidak dipaparkan. Hasilnya masih dikira dan
                # tersedia melalui Bridge Selection yang lebih ringkas di bawah.
            except Exception as e:
                st.warning(f"Engine 2D + Missing + Digit 1st belum dapat dipaparkan: {e}")

            # -----------------------------
            # Selection 2D + Missing yang benar-benar terdapat dalam Bridge
            # -----------------------------
            # Tajuk Bridge digabungkan dengan tajuk formula di atas supaya seragam.
            try:
                bridge_selection_engine = route_engine
                selected_first_positions = {1, 2, 3, 4}
                source_rows = bridge_selection_engine["all"]
                source_rows = source_rows[
                    source_rows["Kedudukan Digit 1st"].isin(selected_first_positions)
                ].copy() if not source_rows.empty else source_rows.copy()

                filtered_rows = []
                for _, source_row in source_rows.iterrows():
                    for bridge_name in ("Bridge V1", "Bridge V2"):
                        bridge_number = str(source_row.get(bridge_name, "")).strip()
                        if not bridge_number or bridge_number.lower() == "nan":
                            continue
                        filtered_rows.append({
                            "Pair": str(source_row["2D"]),
                            "Kedudukan 2D": str(source_row["Kedudukan 2D"]),
                            "No Formula": str(source_row["No Terhasil"]),
                            "Bridge": bridge_name.replace("Bridge ", ""),
                            "No Pilihan": _pad4(bridge_number),
                        })
                bridge_selection_df = pd.DataFrame(
                    filtered_rows,
                    columns=["Pair", "Kedudukan 2D", "No Formula", "Bridge", "No Pilihan"],
                )
                if not bridge_selection_df.empty:
                    bridge_selection_df["Family Key"] = bridge_selection_df["No Pilihan"].map(_key4)
                    bridge_selection_df = bridge_selection_df.drop_duplicates(
                        subset=["Pair", "Kedudukan 2D", "Family Key", "Bridge"]
                    ).reset_index(drop=True)
                    unique_selection_df = bridge_selection_df.drop_duplicates(
                        subset=["Family Key"]
                    ).reset_index(drop=True)
                    selection_numbers = unique_selection_df["No Pilihan"].astype(str).tolist()
                else:
                    unique_selection_df = bridge_selection_df.copy()
                    selection_numbers = []

                st.markdown(
                    f"**Pilihan Bridge V1 ({len(selection_numbers)}):** "
                    f"{' / '.join(selection_numbers) or 'Tiada'}"
                )
                selection_copy_text = (
                    "Rumah A Predictor - 2D Missing Bridge Selection\n\n"
                    f"Jumlah Pilihan: {len(selection_numbers)}\n"
                    f"{' / '.join(selection_numbers) or 'Tiada'}"
                )
                copy_button_clean(
                    "📋 Copy",
                    selection_copy_text,
                    "copy_2d_missing_bridge_selection",
                )

                if not bridge_selection_df.empty:
                    position_priority = {
                        str(row["Kedudukan 2D"]): priority
                        for priority, (_, row) in enumerate(
                            bridge_selection_engine["second_audit"].iterrows(), start=1
                        )
                    }
                    pair_order = list(dict.fromkeys(
                        bridge_selection_df["Pair"].astype(str).tolist()
                    ))
                    pair_order.sort(key=lambda pair_value: min(
                        min(
                            position_priority.get(part.strip(), 999)
                            for part in str(position).split("/")
                        )
                        for position in bridge_selection_df.loc[
                            bridge_selection_df["Pair"].astype(str).eq(pair_value),
                            "Kedudukan 2D",
                        ].astype(str).unique()
                    ))
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(pair_order, start=1):
                        pair_df = bridge_selection_df[
                            bridge_selection_df["Pair"].astype(str).eq(pair_value)
                        ].copy()
                        pair_unique = pair_df.drop_duplicates(subset=["Family Key"])
                        pair_numbers = pair_unique["No Pilihan"].astype(str).tolist()
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan 2D"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_3")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        joint_view, ["Kedudukan 2D"], "Digit 1st + Missing",
                    )
            except Exception as e:
                st.warning(f"2D Missing Bridge Selection belum dapat dipaparkan: {e}")

            # -----------------------------
            # 2D 2nd + dua digit daripada 1st dan 3rd (ikut kemunculan sebenar)
            # -----------------------------
            st.divider()
            st.markdown("**2nd 2D + Digit 1st & 3rd**")
            try:
                first_third_engine = build_2d_first_third_pair_engine(
                    st.session_state.history, first, second, third, lookback=100
                )
                top_positions = first_third_engine["selected_positions"]
                top_position_text = " / ".join(top_positions) or "Tiada"
                all_df = first_third_engine["all"]
                all_numbers = list(dict.fromkeys(
                    all_df["No Terhasil"].astype(str).tolist()
                )) if not all_df.empty else []
                extended_audit = first_third_extended

                st.markdown(f"2nd 2D: {top_position_text}")

                # Senarai mentah semua pair tidak dipaparkan. Pair yang benar-benar
                # terdapat dalam Bridge kekal tersedia di bahagian Selection.
            except Exception as e:
                st.warning(f"2D + Digit 1st & 3rd belum dapat dipaparkan: {e}")

            # -----------------------------
            # Selection: hasil 2D + Digit 1st/3rd yang terdapat dalam Bridge
            # -----------------------------
            # Tajuk Bridge digabungkan dengan tajuk formula di atas supaya seragam.
            try:
                ft_selection_engine = first_third_engine
                ft_source_df = ft_selection_engine["all"].copy()
                v1_lookup = {
                    _key4(number): _pad4(number)
                    for number in bridge_df.get("No", pd.Series(dtype=str)).astype(str)
                } if bridge_df is not None and not bridge_df.empty else {}
                v2_lookup = {
                    _key4(number): _pad4(number)
                    for number in bridge_v2_df.get("No", pd.Series(dtype=str)).astype(str)
                } if bridge_v2_df is not None and not bridge_v2_df.empty else {}

                ft_filtered_rows = []
                for _, source_row in ft_source_df.iterrows():
                    formula_number = str(source_row["No Terhasil"])
                    family_key = _key4(formula_number)
                    for bridge_name, lookup in (("V1", v1_lookup), ("V2", v2_lookup)):
                        bridge_number = lookup.get(family_key, "")
                        if not bridge_number:
                            continue
                        ft_filtered_rows.append({
                            "Pair": str(source_row["2D"]),
                            "Kedudukan 2D": str(source_row["Kedudukan 2D"]),
                            "Pair 1st+3rd": str(source_row["Pair 1st+3rd"]),
                            "No Formula": formula_number,
                            "Bridge": bridge_name,
                            "No Pilihan": bridge_number,
                            "Family Key": family_key,
                        })
                ft_bridge_df = pd.DataFrame(ft_filtered_rows)
                if not ft_bridge_df.empty:
                    ft_bridge_df = ft_bridge_df.drop_duplicates(
                        subset=["Pair", "Kedudukan 2D", "Family Key", "Bridge"]
                    ).reset_index(drop=True)
                    ft_unique_df = ft_bridge_df.drop_duplicates(
                        subset=["Family Key"]
                    ).reset_index(drop=True)
                    ft_selection_numbers = ft_unique_df["No Pilihan"].astype(str).tolist()
                else:
                    ft_unique_df = ft_bridge_df.copy()
                    ft_selection_numbers = []

                st.markdown(
                    f"**Pilihan Bridge V2 ({len(ft_selection_numbers)}):** "
                    f"{' / '.join(ft_selection_numbers) or 'Tiada'}"
                )
                ft_selection_text = (
                    "Rumah A Predictor - 2D 1st & 3rd Bridge Selection\n\n"
                    f"Jumlah Pilihan: {len(ft_selection_numbers)}\n"
                    f"{' / '.join(ft_selection_numbers) or 'Tiada'}"
                )
                copy_button_clean(
                    "📋 Copy",
                    ft_selection_text,
                    "copy_2d_first_third_bridge_selection",
                )

                if not ft_bridge_df.empty:
                    position_priority = {
                        str(row["Kedudukan 2D"]): priority
                        for priority, (_, row) in enumerate(
                            ft_selection_engine["audit"].iterrows(), start=1
                        )
                    }
                    pair_order = list(dict.fromkeys(
                        ft_bridge_df["Pair"].astype(str).tolist()
                    ))
                    pair_order.sort(key=lambda pair_value: min(
                        min(
                            position_priority.get(part.strip(), 999)
                            for part in str(position).split("/")
                        )
                        for position in ft_bridge_df.loc[
                            ft_bridge_df["Pair"].astype(str).eq(pair_value),
                            "Kedudukan 2D",
                        ].astype(str).unique()
                    ))
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(pair_order, start=1):
                        pair_df = ft_bridge_df[
                            ft_bridge_df["Pair"].astype(str).eq(pair_value)
                        ].copy()
                        pair_unique = pair_df.drop_duplicates(subset=["Family Key"])
                        pair_numbers = pair_unique["No Pilihan"].astype(str).tolist()
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan 2D"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_4")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        extended_audit["joint_audit"], ["Kedudukan 2D"],
                        "Digit 1st & 3rd",
                    )
            except Exception as e:
                st.warning(f"2D 1st & 3rd Bridge Selection belum dapat dipaparkan: {e}")

            # -----------------------------
            # -----------------------------
            # 3rd 2D engines
            # -----------------------------
            st.markdown(
                '<div class="engine-head engine-support">3rd 2D Engine</div>',
                unsafe_allow_html=True,
            )
            # 3rd 2D + Missing + Digit 1st (laluan bebas)
            st.markdown("**3rd 2D + Missing**")
            try:
                third_missing_engine = third_missing_route
                third_missing_all = third_missing_engine["all"]
                third_missing_positions_text = " / ".join(
                    third_missing_engine["selected_positions"]
                ) or "Tiada"
                st.markdown(
                    f"3rd 2D: {third_missing_positions_text} &nbsp;&nbsp;|&nbsp;&nbsp; "
                    "Sumber digit: Digit 1st"
                )
            except Exception as e:
                st.warning(f"3rd 2D + Missing belum dapat dipaparkan: {e}")

            # Tajuk Bridge digabungkan dengan tajuk formula di atas supaya seragam.
            try:
                third_missing_bridge_rows = []
                for _, source_row in third_missing_all.iterrows():
                    bridge_number = str(source_row.get("Bridge V1", "")).strip()
                    if not bridge_number or bridge_number.lower() == "nan":
                        continue
                    third_missing_bridge_rows.append({
                        "3rd 2D": str(source_row["2D"]),
                        "Kedudukan": str(source_row["Kedudukan 3rd 2D"]),
                        "No Formula": str(source_row["No Terhasil"]),
                        "Bridge": "V1", "No Pilihan": _pad4(bridge_number),
                        "Key": _key4(bridge_number),
                    })
                third_missing_bridge_df = pd.DataFrame(third_missing_bridge_rows)
                if not third_missing_bridge_df.empty:
                    third_missing_bridge_df = third_missing_bridge_df.drop_duplicates(
                        subset=["Key"]
                    ).reset_index(drop=True)
                    third_missing_bridge_numbers = third_missing_bridge_df["No Pilihan"].astype(str).tolist()
                else:
                    third_missing_bridge_numbers = []
                st.markdown(
                    f"**Pilihan Bridge V1 ({len(third_missing_bridge_numbers)}):** "
                    f"{' / '.join(third_missing_bridge_numbers) or 'Tiada'}"
                )
                third_missing_bridge_copy = (
                    "Rumah A Predictor - 3rd Missing Bridge Selection\n\n"
                    f"Jumlah Pilihan: {len(third_missing_bridge_numbers)}\n"
                    f"{' / '.join(third_missing_bridge_numbers) or 'Tiada'}"
                )
                copy_button_clean(
                    "📋 Copy", third_missing_bridge_copy,
                    "copy_third_missing_bridge",
                )
                if not third_missing_bridge_df.empty:
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(
                        dict.fromkeys(third_missing_bridge_df["3rd 2D"].astype(str)), start=1
                    ):
                        pair_df = third_missing_bridge_df[
                            third_missing_bridge_df["3rd 2D"].astype(str).eq(pair_value)
                        ].copy()
                        pair_numbers = list(dict.fromkeys(pair_df["No Pilihan"].astype(str)))
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_5")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        third_missing_engine["joint_audit"],
                        ["Kedudukan 3rd 2D", "Kedudukan 2D"], "Digit 1st + Missing",
                    )
            except Exception as e:
                st.warning(f"3rd Missing Bridge Selection belum dapat dipaparkan: {e}")

            # -----------------------------
            # 3rd 2D + Digit 1st & 2nd (laluan bebas)
            # -----------------------------
            st.divider()
            st.markdown("**3rd 2D + Digit 1st & 2nd**")
            try:
                third_first_second_engine = third_first_second_route
                third_first_second_all = third_first_second_engine["all"]
                third_first_second_positions_text = " / ".join(
                    third_first_second_engine["selected_positions"]
                ) or "Tiada"
                st.markdown(f"3rd 2D: {third_first_second_positions_text}")
            except Exception as e:
                st.warning(f"3rd 2D + 1st & 2nd belum dapat dipaparkan: {e}")

            # Tajuk Bridge digabungkan dengan tajuk formula di atas supaya seragam.
            try:
                third_first_second_bridge_rows = []
                for _, source_row in third_first_second_all.iterrows():
                    formula = str(source_row["No Terhasil"])
                    key = _key4(formula)
                    bridge_number = v2_route_lookup.get(key, "")
                    if not bridge_number:
                        continue
                    third_first_second_bridge_rows.append({
                        "3rd 2D": str(source_row["2D"]),
                        "Kedudukan": str(source_row["Kedudukan 3rd 2D"]),
                        "Pair 1st+2nd": str(source_row["Pair 1st+2nd"]),
                        "No Formula": formula, "Bridge": "V2",
                        "No Pilihan": bridge_number, "Key": key,
                    })
                third_first_second_bridge_df = pd.DataFrame(third_first_second_bridge_rows)
                if not third_first_second_bridge_df.empty:
                    third_first_second_bridge_df = third_first_second_bridge_df.drop_duplicates(
                        subset=["Key"]
                    ).reset_index(drop=True)
                    third_first_second_bridge_numbers = third_first_second_bridge_df[
                        "No Pilihan"
                    ].astype(str).tolist()
                else:
                    third_first_second_bridge_numbers = []
                st.markdown(
                    f"**Pilihan Bridge V2 ({len(third_first_second_bridge_numbers)}):** "
                    f"{' / '.join(third_first_second_bridge_numbers) or 'Tiada'}"
                )
                third_first_second_bridge_copy = (
                    "Rumah A Predictor - 3rd 1st & 2nd Bridge Selection\n\n"
                    f"Jumlah Pilihan: {len(third_first_second_bridge_numbers)}\n"
                    f"{' / '.join(third_first_second_bridge_numbers) or 'Tiada'}"
                )
                copy_button_clean(
                    "📋 Copy",
                    third_first_second_bridge_copy, "copy_third_first_second_bridge",
                )
                if not third_first_second_bridge_df.empty:
                    _pair_groups = []
                    for pair_index, pair_value in enumerate(
                        dict.fromkeys(third_first_second_bridge_df["3rd 2D"].astype(str)), start=1
                    ):
                        pair_df = third_first_second_bridge_df[
                            third_first_second_bridge_df["3rd 2D"].astype(str).eq(pair_value)
                        ].copy()
                        pair_numbers = list(dict.fromkeys(pair_df["No Pilihan"].astype(str)))
                        pair_positions = " / ".join(dict.fromkeys(
                            pair_df["Kedudukan"].astype(str).tolist()
                        ))
                        _pair_groups.append({"Pair": pair_value, "Kedudukan": pair_positions, "Calon": list(pair_numbers)})
                    render_pair_groups(_pair_groups, "eng_pairs_6")
                with st.expander("Lihat audit sejarah - 100 draw", expanded=False):
                    _show_uniform_2d_audit(
                        third_first_second_engine["audit"],
                        ["Kedudukan 3rd 2D", "Kedudukan 2D"], "Digit 1st & 2nd",
                    )
            except Exception as e:
                st.warning(f"3rd 1st & 2nd Bridge Selection belum dapat dipaparkan: {e}")


            # Carta 3D V2 - Menegak/L sahaja untuk Historical Signal Engine
            # -----------------------------
            st.markdown('<div class="engine-head engine-chart">Carta 3D V2</div>', unsafe_allow_html=True)
            st.caption(
                "Jumlah digit dan campur silang untuk pilihan 3D Menegak/L. "
                "Pilihan ini menjadi input dalaman Historical Signal Engine."
            )
            try:
                chart_v2_text, _, chart_v2_meta = build_chart_3d_signal_v31_39(
                    first, second, third, bridge_df, bridge_v2_df
                )
                st.code("\n".join(chart_v2_meta.get("Rows", [])), language=None)
                chart_3d_df = chart_v2_meta.get("3D Choices", pd.DataFrame())
                chart_3d_confirmed_df = chart_v2_meta.get("3D Confirmed", pd.DataFrame())
                vertical_values = chart_3d_df[chart_3d_df["Pilihan"] == "Menegak"]["3D"].tolist() if not chart_3d_df.empty else []
                l_values = chart_3d_df[chart_3d_df["Pilihan"] != "Menegak"]["3D"].tolist() if not chart_3d_df.empty else []
                st.markdown(
                    f'**Pilihan Menegak:** {" / ".join(vertical_values) or "Tiada"}  \n'
                    f'**Pilihan L:** {" / ".join(l_values) or "Tiada"}  \n'
                    f'**Carta 3D + Bridge:** {len(chart_3d_confirmed_df)}'
                )
                copy_button_clean(
                    "📋 Copy Carta 3D V2",
                    chart_v2_text,
                    "copy_chart_3d_v2_v31_39",
                )

            except Exception as e:
                st.warning(f"Carta 3D V2 belum dapat dipaparkan: {e}")
