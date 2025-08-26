# CRM Project Setup

This document provides all the steps needed to set up the CRM project, run migrations, start Celery workers and Beat, configure cron jobs, and verify scheduled tasks.

---

             ## 1. Install Dependencies

Ensure you have Python 3, pip, Redis, and virtualenv installed.
sudo apt update
sudo apt install redis-server
pip install -r requirements.txt

               2. Apply Migrations
Run the following command to apply Django migrations:
python manage.py migrate
               3. Start Celery Worker
In one terminal, start the Celery worker to handle asynchronous tasks:
celery -A crm worker -l info

               4. Start Celery Beat
In another terminal, start Celery Beat to schedule periodic tasks:
celery -A crm beat -l info

                5. Cron Jobs
The project uses system cron and django-crontab for scheduled tasks.

                5.1 Customer Cleanup
Script: crm/cron_jobs/clean_inactive_customers.sh
Schedule: Every Sunday at 2:00 AM
Log file: /tmp/customer_cleanup_log.txt
Crontab entry file: crm/cron_jobs/customer_cleanup_crontab.txt
cat /tmp/customer_cleanup_log.txt
                5.2 Order Reminders
Script: crm/cron_jobs/send_order_reminders.py
Schedule: Daily at 8:00 AM
Log file: /tmp/order_reminders_log.txt
Crontab entry file: crm/cron_jobs/order_reminders_crontab.txt
cat /tmp/order_reminders_log.txt

                 5.3 Heartbeat Logger
Job defined in crm/cron.py (log_crm_heartbeat)
Schedule: Every 5 minutes
Log file: /tmp/crm_heartbeat_log.txt
cat /tmp/crm_heartbeat_log.txt
                 
                 5.4 Low Stock Updates
Job defined in crm/cron.py (update_low_stock)
Schedule: Every 12 hours
Log file: /tmp/low_stock_updates_log.txt
cat /tmp/low_stock_updates_log.txt

                 6. Celery Task: CRM Report
Task defined in crm/tasks.py (generatecrmreport)
Schedule: Weekly via Celery Beat
Logs: /tmp/crmreportlog.txt
cat /tmp/crmreportlog.txt

                  7. Notes
Ensure Redis server is running before starting Celery:
sudo service redis-server start
Cron jobs append to log files; do not delete logs while tasks are running.
Celery logs can help debug scheduled tasks if they fail.
All scripts and tasks include timestamps in logs for easier tracking.

