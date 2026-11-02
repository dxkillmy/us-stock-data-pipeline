"""Integration tests: these run against a real PostgreSQL database (test_db)."""
from datetime import date
from decimal import Decimal

import pandas as pd

from utils.database import save_raw_prices, transform_to_analytics, get_last_dates


def make_prices(rows):
    """rows: list of (date string, close). Builds a DataFrame shaped like the yfinance output."""
    days = [pd.Timestamp(d).date() for d, _ in rows]
    closes = [c for _, c in rows]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1 for c in closes],
            "Low": [c - 1 for c in closes],
            "Close": closes,
            "Volume": [1000] * len(rows),
        },
        index=days,
    )


def count_rows(conn, table):
    with conn, conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        return cur.fetchone()[0]


THREE_DAYS = [("2026-10-20", 100.0), ("2026-10-21", 110.0), ("2026-10-22", 99.0)]


def test_loading_same_data_twice_does_not_duplicate(db_conn):
    df = make_prices(THREE_DAYS)
    save_raw_prices(db_conn, "AAPL", df)
    save_raw_prices(db_conn, "AAPL", df)
    assert count_rows(db_conn, "raw.stock_prices") == 3


def test_reloading_a_day_replaces_the_old_values(db_conn):
    # Like an unfinished candle that gets replaced by the final one on the next run.
    save_raw_prices(db_conn, "AAPL", make_prices([("2026-10-22", 99.0)]))
    save_raw_prices(db_conn, "AAPL", make_prices([("2026-10-22", 105.0)]))

    with db_conn, db_conn.cursor() as cur:
        cur.execute("SELECT close FROM raw.stock_prices WHERE ticker = 'AAPL';")
        assert cur.fetchall() == [(Decimal("105.0000"),)]


def test_daily_change_pct_compares_with_previous_close(db_conn):
    save_raw_prices(db_conn, "AAPL", make_prices(THREE_DAYS))
    transform_to_analytics(db_conn)

    with db_conn, db_conn.cursor() as cur:
        cur.execute("""
            SELECT daily_change_pct FROM analytics.fact_stock_prices
            WHERE ticker = 'AAPL' ORDER BY trade_date;
        """)
        changes = [r[0] for r in cur.fetchall()]

    assert changes == [None, Decimal("10.00"), Decimal("-10.00")]


def test_daily_change_pct_does_not_mix_tickers(db_conn):
    save_raw_prices(db_conn, "AAPL", make_prices([("2026-10-21", 100.0), ("2026-10-22", 110.0)]))
    save_raw_prices(db_conn, "MSFT", make_prices([("2026-10-21", 500.0), ("2026-10-22", 450.0)]))
    transform_to_analytics(db_conn)

    with db_conn, db_conn.cursor() as cur:
        cur.execute("""
            SELECT ticker, daily_change_pct FROM analytics.fact_stock_prices
            WHERE trade_date = '2026-10-22' ORDER BY ticker;
        """)
        assert cur.fetchall() == [("AAPL", Decimal("10.00")), ("MSFT", Decimal("-10.00"))]


def test_running_transform_twice_does_not_duplicate(db_conn):
    save_raw_prices(db_conn, "AAPL", make_prices(THREE_DAYS))
    transform_to_analytics(db_conn)
    transform_to_analytics(db_conn)
    assert count_rows(db_conn, "analytics.fact_stock_prices") == 3


def test_get_last_dates_returns_latest_day_per_ticker(db_conn):
    save_raw_prices(db_conn, "AAPL", make_prices(THREE_DAYS))
    save_raw_prices(db_conn, "MSFT", make_prices([("2026-10-20", 500.0)]))
    assert get_last_dates(db_conn) == {"AAPL": date(2026, 10, 22), "MSFT": date(2026, 10, 20)}


def test_transform_marks_trading_days(db_conn):
    save_raw_prices(db_conn, "AAPL", make_prices(THREE_DAYS))
    transform_to_analytics(db_conn)

    with db_conn, db_conn.cursor() as cur:
        cur.execute("""
            SELECT full_date FROM analytics.dim_date
            WHERE is_trading_day AND full_date BETWEEN '2026-10-19' AND '2026-10-25'
            ORDER BY full_date;
        """)
        days = [r[0] for r in cur.fetchall()]
    assert days == [date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22)]