from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PIPELINES_DIR = "/usr/local/airflow/pipelines"  # repo-root pipelines/
DBT_DIR = "/usr/local/airflow/dbt"  # repo-root dbt/, mounted in docker-compose.override.yml

with DAG(
    dag_id="nigeria_economic_indicators_pipeline",
    description="World Bank API -> MotherDuck bronze -> dbt silver/gold",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",  # runs once every day at midnight UTC
    catchup=False,
    tags=["nigeria", "economic-indicators"],
) as dag:
    extract_worldbank_data = BashOperator(
        task_id="extract_worldbank_data",
        bash_command=f"python {PIPELINES_DIR}/world-bank/extract.py",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"dbt run --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"dbt test --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    extract_worldbank_data >> dbt_run >> dbt_test
