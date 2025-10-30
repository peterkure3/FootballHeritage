"""
Airflow DAG for football betting pipeline orchestration.
Runs weekly: fetch → transform → load → train → predict
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from config import AIRFLOW_DAG_SCHEDULE, AIRFLOW_DAG_CATCHUP

# Import pipeline functions
from etl.fetch_raw_data import main as fetch_data
from etl.transform import main as transform_data
from etl.load_to_db import main as load_data
from models.train_model import main as train_model
from models.predict import main as predict_matches


# Default arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    "football_betting_pipeline",
    default_args=default_args,
    description="Weekly football betting data pipeline and model training",
    schedule_interval=AIRFLOW_DAG_SCHEDULE,
    start_date=datetime(2025, 1, 1),
    catchup=AIRFLOW_DAG_CATCHUP,
    tags=["football", "betting", "ml"],
)

# Task 1: Fetch raw data
fetch_task = PythonOperator(
    task_id="fetch_raw_data",
    python_callable=fetch_data,
    dag=dag,
)

# Task 2: Transform data
transform_task = PythonOperator(
    task_id="transform_data",
    python_callable=transform_data,
    dag=dag,
)

# Task 3: Load to database
load_task = PythonOperator(
    task_id="load_to_database",
    python_callable=load_data,
    dag=dag,
)

# Task 4: Train model
train_task = PythonOperator(
    task_id="train_model",
    python_callable=train_model,
    dag=dag,
)

# Task 5: Generate predictions
predict_task = PythonOperator(
    task_id="generate_predictions",
    python_callable=predict_matches,
    dag=dag,
)

# Task 6: Cleanup old files (optional)
cleanup_task = BashOperator(
    task_id="cleanup_old_files",
    bash_command=f"""
    # Remove raw data older than 30 days
    find {project_root}/data/raw -type f -mtime +30 -delete || true
    # Remove interim data older than 7 days
    find {project_root}/data/interim -type f -mtime +7 -delete || true
    """,
    dag=dag,
)

# Define task dependencies
fetch_task >> transform_task >> load_task >> train_task >> predict_task >> cleanup_task
