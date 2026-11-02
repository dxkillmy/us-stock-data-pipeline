import os

import pytest

from utils.database import get_db_connection, setup_database, load_dim_stock


@pytest.fixture
def db_conn():
    if not os.getenv("DB_NAME", "").endswith("test_db"):
        pytest.skip("integration tests only run when DB_NAME ends with 'test_db'")

    conn = get_db_connection()
    setup_database(conn)
    load_dim_stock(conn)
    yield conn

    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE raw.stock_prices, analytics.fact_stock_prices;")
        cur.execute("UPDATE analytics.dim_date SET is_trading_day = FALSE;")
    conn.close()