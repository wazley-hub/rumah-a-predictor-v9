"""Ujian ringkas: python test_ranking_engine.py"""
import pandas as pd
import ranking_engine as r


def _hist(rows):
    return pd.DataFrame(rows, columns=["first", "second", "third"])


def test_route_lift_removes_coverage_bias():
    # Laluan A (liputan besar) dan B (liputan kecil) hit sama kerap -> lift B lebih tinggi
    matches = [{"a_hit": i % 4 == 0, "a_exp": 0.40, "b_hit": i % 4 == 0, "b_exp": 0.10} for i in range(40)]
    assert r.route_lift(matches, "b_hit", "b_exp") > r.route_lift(matches, "a_hit", "a_exp")


def test_ranking_changes_with_draw():
    base = [[f"{(i*37)%10000:04d}", f"{(i*91+5)%10000:04d}", f"{(i*53+9)%10000:04d}"] for i in range(80)]
    a = r.build_bridge_pair_priority_dynamic(_hist(base), *base[-1])
    base2 = base + [["1234", "5678", "9012"]]
    b = r.build_bridge_pair_priority_dynamic(_hist(base2), *base2[-1])
    assert list(a["Current Pair"]) != list(b["Current Pair"])
    assert a["Skor %"].is_monotonic_decreasing and b["Skor %"].is_monotonic_decreasing


def test_no_future_leak_in_ranking():
    base = [[f"{(i*37)%10000:04d}", f"{(i*91+5)%10000:04d}", f"{(i*53+9)%10000:04d}"] for i in range(80)]
    t = r.build_pair_table(_hist(base))
    a = r.rank_pairs_from_table(t, 60)
    t2 = t.copy()
    t2.loc[t2["src"] >= 60, ["hit", "v1_hit", "v2_hit"]] = 1.0  # ubah masa depan
    b = r.rank_pairs_from_table(t2, 60)
    assert a[["Current Pair", "Skor %"]].equals(b[["Current Pair", "Skor %"]])


def test_pair_numbers_ordered_by_box_chance():
    df = pd.DataFrame({"Pair": "11", "No": ["1122", "1234"], "Route": ["Bridge V1", "Bridge V1"]})
    out = r.rank_pair_numbers(df, None)
    assert out.loc[0, "No"] == "1234"


def test_topn_caps():
    f = {"A": pd.DataFrame({"No Terhasil": [f"{i:04d}" for i in range(100)]})}
    assert len(r.rank_candidates_consensus(f, top_n=10)) == 10


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
