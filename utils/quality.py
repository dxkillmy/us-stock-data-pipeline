def validate_prices(df):
    prices = df[["Open", "High", "Low", "Close"]]

    ok = prices.notna().all(axis=1) & df["Volume"].notna()
    ok &= (prices > 0).all(axis=1)
    ok &= df["High"] >= df["Low"]   
    ok &= df["Volume"] >= 0

    return df[ok], int((~ok).sum())