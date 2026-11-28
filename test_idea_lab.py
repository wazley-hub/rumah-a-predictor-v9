"""Ujian ringkas: python test_idea_lab.py"""
import pandas as pd
import idea_lab as lab


def _prizes(n=400):
    return [[f"{(i * 37) % 10000:04d}", f"{(i * 91 + 5) % 10000:04d}", f"{(i * 53 + 9) % 10000:04d}"] for i in range(n)]


def test_strategies_use_only_past_draws():
    for key in ("kerap", "jarang", "digit", "terbitan"):
        spec = lab.IDEAS[key]
        s = spec["cls"](50) if spec["uses_window"] else spec["cls"]()
        for d in _prizes(60):
            s.update(d)
        before = s.pick(5)
        again = s.pick(5)
        assert before == again          # pilihan tidak berubah tanpa data baharu


def test_future_draw_is_never_picked_by_frequency():
    prizes = [["1111", "2222", "3333"]] * 80 + [["9999", "8888", "7777"]]
    r = lab.run_idea(prizes, "kerap", window=50, n_picks=3, test_draws=41, match="exact")
    v = r["halves"]["pengesahan"]
    assert v["hit"] == v["n"] - 1       # semua draw berulang dikenali, tetapi draw baharu yang terakhir TIDAK diramal


def test_random_control_is_not_confirmed_and_tracker_corrects():
    h = _prizes(1200)
    r = lab.run_idea(h, "rawak", 0, 10, 1000, "box")
    assert not lab.verdict(r, 1).startswith("Disahkan")
    tr = lab.Tracker()
    for _ in range(4):
        tr.add(r)
    t = tr.table()
    assert len(t) == 4 and (t["p terlaras"] >= t["p pengesahan"]).all()


def test_verdict_logic():
    base = {"halves": {"penemuan": {"n": 500, "hit": 50, "hit_pct": 10.0, "exp_pct": 6.0, "p": 0.01},
                       "pengesahan": {"n": 500, "hit": 20, "hit_pct": 4.0, "exp_pct": 6.0, "p": 0.9}}}
    assert lab.verdict(base, 1).startswith("Tidak disahkan")
    good = {"halves": {"penemuan": {"n": 500, "hit": 50, "hit_pct": 10.0, "exp_pct": 6.0, "p": 0.01},
                       "pengesahan": {"n": 500, "hit": 55, "hit_pct": 11.0, "exp_pct": 6.0, "p": 0.001}}}
    assert lab.verdict(good, 1).startswith("Disahkan") and not lab.verdict(good, 100).startswith("Disahkan")


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
