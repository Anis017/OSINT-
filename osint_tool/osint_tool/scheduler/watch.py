# scheduler/watcher.py
from apscheduler.schedulers.background import BackgroundScheduler
import time

def scheduled_scan(target, username, location, context):
    # This will call your main function
    from main import run_investigation
    print(f"Running scheduled scan for {target}")
    run_investigation(target, username, location, context)

def start_watcher(target, username, location, context, interval_minutes=60):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scheduled_scan,
        'interval',
        minutes=interval_minutes,
        args=[target, username, location, context]
    )
    scheduler.start()
    print(f"Watcher started, scanning every {interval_minutes} minutes.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()