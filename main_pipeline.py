import warnings
warnings.filterwarnings("ignore", module="yfinance")
from datetime import date
import sys
import os
import time
import yfinance as yf
from dotenv import load_dotenv

load_dotenv() 

from utils.alert import send_discord_alert
from utils.quality import validate_prices
from utils.database import (
    get_db_connection, get_last_dates, setup_database, load_dim_stock, save_raw_prices, transform_to_analytics,
)

BACKFILL_START = date.fromisoformat(os.getenv("BACKFILL_START", "2021-10-01"))
FULL_BACKFILL = os.getenv("FULL_BACKFILL") == "1"


def fetch_prices(symbol, start):
    try:
        df = yf.Ticker(symbol).history(start=start, auto_adjust=False)
    except Exception as e:
        raise RuntimeError(f"download failed ({type(e).__name__})") from None
    if df.empty:
        raise RuntimeError("no data returned")
    df.index = df.index.date
    return df


def run_pipeline():
    send_discord_alert(f" Starting Stock Data Pipeline (backfill_start={BACKFILL_START}, full={FULL_BACKFILL})")
    conn = get_db_connection()
    setup_database(conn)
    symbols = load_dim_stock(conn)
    last_dates = get_last_dates(conn)

    success, failed, bad_rows = 0, [], 0
    for symbol in symbols:
        try:
            last = last_dates.get(symbol)
            start = BACKFILL_START if (FULL_BACKFILL or last is None) else last
            df = fetch_prices(symbol, start)
            df, rejected = validate_prices(df)
            bad_rows += rejected
            if df.empty:
                raise ValueError("all rows rejected by quality checks")
            save_raw_prices(conn, symbol, df)
            print(f"Ingested {symbol} ({len(df)} rows)")
            success += 1
        except Exception as e:
            print(f"⚠️ {symbol} failed: {e}")
            failed.append(symbol)
        time.sleep(1)

    transform_to_analytics(conn)
    conn.close()

    send_discord_alert(
        f" Pipeline Completed!\n Successful: `{success}`\n Failed: `{failed}`\n"
        f" Rows rejected by quality checks: `{bad_rows}`"
    )
    if not success:
        raise SystemExit(1)


def cmd_setup():
    conn = get_db_connection()
    try:
        setup_database(conn)
        load_dim_stock(conn)
    finally:
        conn.close()


def cmd_ingest(symbol):
    conn = get_db_connection()
    try:
        last = get_last_dates(conn).get(symbol)
        start = BACKFILL_START if (FULL_BACKFILL or last is None) else last
        df = fetch_prices(symbol, start)
        df, rejected = validate_prices(df)
        if df.empty:
            raise ValueError("all rows rejected by quality checks")
        save_raw_prices(conn, symbol, df)
        print(f" Ingested {symbol} ({len(df)} rows, rejected={rejected})")
    finally:
        conn.close()


def cmd_transform():
    conn = get_db_connection()
    try:
        transform_to_analytics(conn)
    finally:
        conn.close()


def cmd_notify():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker), MAX(trade_date) FROM raw.stock_prices;")
            rows, tickers, latest = cur.fetchone()
    finally:
        conn.close()
    send_discord_alert(f" Pipeline finished\n Rows: `{rows}` | Tickers: `{tickers}` | Latest: `{latest}`")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "all":
        run_pipeline()
    elif cmd == "setup":
        cmd_setup()
    elif cmd == "ingest":
        cmd_ingest(sys.argv[2])
    elif cmd == "transform":
        cmd_transform()
    elif cmd == "notify":
        cmd_notify()
    else:
        raise SystemExit(f"unknown command: {cmd}")