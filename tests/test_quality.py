import pandas as pd
from utils.quality import validate_prices

def make_df(**overrides):
    row = {"Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 103.0, "Volume": 1000}
    row.update(overrides)
    return pd.DataFrame([row])

def test_good_row_passes():
    df, rejected = validate_prices(make_df())
    assert len(df) == 1 and rejected == 0

def test_bad_rows_are_rejected():
    bad_cases = [
        {"Close": float("nan")},
        {"Open": -1.0},
        {"Close": 0.0},
        {"High": 90.0},
        {"Volume": -5},
    ]
    for overrides in bad_cases:
        df, rejected = validate_prices(make_df(**overrides))
        assert df.empty and rejected == 1, overrides

def test_only_bad_rows_are_removed():
    df = pd.concat([make_df(), make_df(Open=-1.0)], ignore_index=True)
    clean, rejected = validate_prices(df)
    assert len(clean) == 1 and rejected == 1

def test_incomplete_candle_from_open_market_is_rejected():
    df, rejected = validate_prices(make_df(Close=float("nan"), Volume=float("nan")))
    assert df.empty and rejected == 1

def test_missing_volume_is_rejected():
    df, rejected = validate_prices(make_df(Volume=float("nan")))
    assert df.empty and rejected == 1