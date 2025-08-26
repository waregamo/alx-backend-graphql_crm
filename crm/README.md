# CRM Project Setup

## Install Dependencies
sudo apt update
sudo apt install redis-server
pip install -r requirements.txt

## Apply Migrations
python manage.py migrate

## Start Celery Worker
celery -A crm worker -l info

## Start Celery Beat
celery -A crm beat -l info

## Verify Logs
cat /tmp/crmreportlog.txt
cat /tmp/customer_cleanup_log.txt
cat /tmp/order_reminders_log.txt
cat /tmp/crm_heartbeat_log.txt
cat /tmp/low_stock_updates_log.txt

## Notes
sudo service redis-server start
