import csv
from datetime import timedelta

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

RUN = "cd /opt/airflow/pipeline && python3 main_pipeline.py"

with open("/opt/airflow/pipeline/data/stocks.csv", newline="", encoding="utf-8") as f:
    SYMBOLS = [r["ticker"] for r in csv.DictReader(f)]

with DAG(
    dag_id="stock_pipeline",
    schedule="0 17 * * 1-5",
    start_date=pendulum.datetime(2026, 10, 1, tz="America/New_York"),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["stocks"],
) as dag:

    setup = BashOperator(task_id="setup", bash_command=f"{RUN} setup", append_env=True)

    ingest = BashOperator.partial(
        task_id="ingest", append_env=True, max_active_tis_per_dag=4,
    ).expand(bash_command=[f"{RUN} ingest {s}" for s in SYMBOLS])

    transform = BashOperator(
        task_id="transform", bash_command=f"{RUN} transform",
        trigger_rule="none_failed_min_one_success", append_env=True,
    )

    notify = BashOperator(
        task_id="notify", bash_command=f"{RUN} notify",
        trigger_rule="all_done", append_env=True,
    )

    setup >> ingest >> transform >> notify