sudo apt update
sudo apt install redis-server
pip install -r requirements.txt
python manage.py migrate
celery -A crm worker -l info
celery -A crm beat -l info
cat /tmp/crmreportlog.txt
cat /tmp/customer_cleanup_log.txt
cat /tmp/order_reminders_log.txt
cat /tmp/crm_heartbeat_log.txt
cat /tmp/low_stock_updates_log.txt
sudo service redis-server start
