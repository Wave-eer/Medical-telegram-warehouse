import os
import subprocess
from dagster import op, job, schedule, DefaultScheduleStatus

@op
def scrape_telegram_data():
    """Runs the Telegram scraper to retrieve JSON data and download raw images."""
    result = subprocess.run(["python", "src/scraper.py"], capture_output=True, text=True, check=True)
    print(result.stdout)
    return True

@op
def load_raw_to_postgres(start):
    """Loads raw messages JSON data from data lake into PostgreSQL database."""
    result = subprocess.run(["python", "src/load_raw.py"], capture_output=True, text=True, check=True)
    print(result.stdout)
    return True

@op
def run_yolo_enrichment(start):
    """Scans downloaded images, executes object detection using YOLOv8, and writes results to DB."""
    result = subprocess.run(["python", "src/yolo_detect.py"], capture_output=True, text=True, check=True)
    print(result.stdout)
    return True

@op
def run_dbt_transformations(raw_loaded, yolo_completed):
    """Runs dbt staging and marts models to transform raw PostgreSQL data into star schema structures."""
    # Run dbt run
    run_res = subprocess.run(
        ["dbt", "run", "--project-dir", "medical_warehouse", "--profiles-dir", "medical_warehouse"],
        capture_output=True, text=True, check=True
    )
    print(run_res.stdout)
    
    # Run dbt test
    test_res = subprocess.run(
        ["dbt", "test", "--project-dir", "medical_warehouse", "--profiles-dir", "medical_warehouse"],
        capture_output=True, text=True, check=True
    )
    print(test_res.stdout)
    return True

@job
def medical_data_pipeline():
    # Define job dependencies
    scraped = scrape_telegram_data()
    raw_loaded = load_raw_to_postgres(scraped)
    yolo_completed = run_yolo_enrichment(scraped)
    run_dbt_transformations(raw_loaded=raw_loaded, yolo_completed=yolo_completed)

# Daily Schedule
@schedule(cron_expression="0 0 * * *", job=medical_data_pipeline, default_status=DefaultScheduleStatus.STOPPED)
def daily_medical_pipeline_schedule():
    return {}
