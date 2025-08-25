import os
from datetime import datetime
import requests

LOG_FILE = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_URL = "http://localhost:8000/graphql"

def log_crm_heartbeat():
    """
    Logs a heartbeat message every 5 minutes to check CRM health.
    Optionally queries GraphQL 'hello' field.
    """
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{timestamp} CRM is alive"

    # Append heartbeat message
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

    # Optional: Check GraphQL hello field
    try:
        query = {"query": "{ hello }"}
        response = requests.post(GRAPHQL_URL, json=query)
        if response.ok:
            data = response.json()
            hello_msg = data.get("data", {}).get("hello")
            if hello_msg:
                with open(LOG_FILE, "a") as f:
                    f.write(f"{timestamp} GraphQL hello → {hello_msg}\n")
    except Exception as e:
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp} GraphQL check failed: {e}\n")
