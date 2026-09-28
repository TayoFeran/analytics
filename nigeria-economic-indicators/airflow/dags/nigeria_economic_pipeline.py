from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/usr/local/airflow/project"
DBT_DIR = f"{PROJECT_DIR}/dbt"

with DAG(
    dag_id="nigeria_economic_indicators_pipeline",
    description="World Bank API -> MotherDuck bronze -> dbt silver/analytics",
    start_date=datetime(2026, 1, 1),
    schedule=None,      # manual trigger only, for now
    catchup=False,
    tags=["nigeria", "economic-indicators"],
) as dag:

    extract_worldbank_data = BashOperator(
        task_id="extract_worldbank_data",
        bash_command=f"python {PROJECT_DIR}/extract.py",
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