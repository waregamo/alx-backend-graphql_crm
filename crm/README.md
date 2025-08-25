# CRM Celery Setup

This guide walks you through setting up Celery with Redis for the CRM project and running scheduled tasks.

---

## Requirements

* **Redis** (task broker)

  ```bash
  sudo apt install redis-server
  ```
* **Python dependencies** (listed in `requirements.txt`)

---

## Setup Instructions

### 1. Install Dependencies

```bash
# Update system packages and install Redis (Linux example)
sudo apt update
sudo apt install redis-server

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Database Migrations

```bash
python manage.py migrate
```

### 3. Run Celery

Start the Celery worker and Beat scheduler:

```bash
# From project root, start Celery worker
celery -A crm worker -l info

# From project root, start Celery Beat (for scheduled tasks)
celery -A crm beat -l info
```

### 4. Verify CRM Reports

Check that CRM reports are being generated:

```bash
cat /tmp/crm_report_log.txt
```

---

## ⚡ Notes

* Make sure Redis server is running before starting Celery.
* Celery logs will help you debug issues if scheduled tasks don’t run.
