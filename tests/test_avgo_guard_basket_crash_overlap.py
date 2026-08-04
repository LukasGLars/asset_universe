import pandas as pd

import run_avgo_guard_basket_crash_overlap as ov


def test_solo_vs_basket_crash_classified_and_forward_returns_computed(monkeypatch, tmp_path, capsys):
    dates = pd.date_range("2020-01-01", periods=40, freq="D")
    avgo = pd.Series([100.0] * 40, index=dates)
    avgo.iloc[5] = 100.0
    avgo.iloc[10] = 88.0   # solo crash: -12% over 5 days, no peers crashing
    avgo.iloc[12] = 92.0   # +4.5% vs 88 at 2d out
    avgo.iloc[14] = 95.0   # +8.0% vs 88 at 4d out
    avgo.iloc[15] = 100.0
    avgo.iloc[20] = 88.0   # basket crash: -12% over 5 days, 2 peers also crashing
    avgo.iloc[22] = 80.0   # -9.1% vs 88 at 2d out
    avgo.iloc[24] = 75.0   # -14.8% vs 88 at 4d out

    peer = pd.Series([100.0] * 40, index=dates)
    peer.iloc[15] = 100.0
    peer.iloc[20] = 85.0   # -15% over 5 days -- crashes alongside AVGO at t=20 only

    monkeypatch.setattr(ov, "DECLUSTER_MIN_GAP", 3)
    monkeypatch.setattr(ov, "FWD_HORIZONS", [2, 4])
    monkeypatch.setattr(ov, "PEERS", ["P1", "P2"])
    monkeypatch.setattr(ov.reader, "ticker_path", lambda *a, **k: "dummy")
    monkeypatch.setattr(ov.reader, "load", lambda path: pd.DataFrame({"close": avgo}))
    monkeypatch.setattr(ov, "_fetch_peer_prices", lambda ticker: peer.copy())

    ov.main()
    out = capsys.readouterr().out
    assert "AVGO crash-ROC events (5d <=-10%), declustered: 2" in out
    assert "SOLO crash (AVGO alone) (n=1)" in out
    assert "BASKET crash (>=2 semi peers also crashing) (n=1)" in out
    assert "2d: median +4.5%  win 100%" in out   # solo bucket bounced
    assert "2d: median -9.1%  win 0%" in out     # basket bucket kept falling
