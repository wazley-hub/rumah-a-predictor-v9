"""Ujian ringkas: python test_scoreboard.py"""
import pandas as pd
import scoreboard as sb
import ranking_engine as re_


def _history(rows):
    return pd.DataFrame(rows, columns=["draw_no", "first", "second", "third"])


def test_draw_id_normalises():
    assert sb.draw_id("621426") == "621426" and sb.draw_id(621426.0) == "621426"


def test_perfect_and_missing_predictions():
    h = _history([[str(100 + i), "1234", "5678", "9012"] for i in range(60)])
    # ramalan setiap draw sumber mengandungi keluarga 1234 -> sentiasa kena pada draw seterusnya
    cache = {str(100 + i): sb.make_entry([re_.key4("1234")], [re_.key4("1234")]) for i in range(59)}
    r = sb.evaluate(cache, h, window=50)
    top10 = [x for x in r["rows"] if x["key"] == ("top", 10)][0]
    assert top10["hit"] == top10["n"] == 50 and len(r["missing"]) == 0
    r2 = sb.evaluate({}, h, window=20)
    assert r2["rows"] == [] and len(r2["missing"]) == 20


def test_expected_matches_coverage_and_verdict_needs_correction():
    h = _history([[str(100 + i), "1234", "5678", "9012"] for i in range(60)])
    cache = {str(100 + i): sb.make_entry([re_.key4("1111")], [re_.key4("1111")]) for i in range(59)}   # tidak pernah kena
    r = sb.evaluate(cache, h, window=50)
    row = [x for x in r["rows"] if x["key"] == ("top", 10)][0]
    assert row["hit"] == 0 and row["verdict"] == "Setara rawak"
    assert abs(row["exp_pct"] - re_.route_chance([re_.key4("1111")]) * 100) < 1e-9


def test_only_completed_draws_count():
    h = _history([[str(100 + i), "1234", "5678", "9012"] for i in range(10)])
    assert sb.completed_sources(h, 100) == [str(100 + i) for i in range(9)]   # draw terakhir belum ada keputusan


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
