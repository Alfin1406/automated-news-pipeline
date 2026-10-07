from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'alfin_data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    'pln_icon_plus_pipeline',
    default_args=default_args,
    schedule_interval='0 22 * * 0', 
    catchup=False, 
    description='Pipeline ETL Otomatis PLN Icon Plus (Incremental Load)',
    tags=['pln_icon_plus', 'ai_dashboard', 'finops'],
) as dag:

    # Tahap 1: Extract & Clean
    task_scrape_cnbc = BashOperator(
        task_id='scrape_cnbc_tech',
        bash_command='cd /opt/airflow/dags && python scraper_ai_cnbc.py'
    )

    task_scrape_detik = BashOperator(
        task_id='scrape_detik_inet',
        bash_command='cd /opt/airflow/dags && python scraper_detik.py'
    )
    
    task_scrape_rundown = BashOperator(
        task_id='scrape_therundown_ai',
        bash_command='cd /opt/airflow/dags && python scraper_therundown.py'
    )

    # Tahap 2: Transform (AI Enrichment dengan Incremental Logic)
    task_ai_enrichment = BashOperator(
        task_id='ai_enrichment_filter',
        bash_command='cd /opt/airflow/dags && python ai_enrichment.py'
    )

    # Tahap 3: Load ke Database
    task_load_db = BashOperator(
        task_id='load_to_postgres',
        bash_command='cd /opt/airflow/dags && python load_to_db.py'
    )

    # Alur Kerja Microservices (Eksekusi 3 Scraper Paralel -> NLP -> Database)
    [task_scrape_cnbc, task_scrape_detik, task_scrape_rundown] >> task_ai_enrichment >> task_load_db